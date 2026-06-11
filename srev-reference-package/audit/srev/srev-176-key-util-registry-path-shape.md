# SREV-176: Key Utility Registry Path Shape

## Stage Gate

```text
stage: schema -> boundary -> topology -> logic -> action -> verify
input artifact: Sandboxie/core/dll/key_util.c, Key_GetName, OBJECT_ATTRIBUTES, KEY_NAME_INFORMATION, ZwQueryKey
output artifact: key utility helpers consume the existing key-name owner for counted registry names and build CLSID paths with exact bounded storage
owner: Sandboxie/core/dll/key_util.c
acceptance gate: docs/plan/check-srev-176.py and docs/plan/check-srev-176.sh
```

## Data

`key_util.c` owns helper paths used by Sandboxie's DLL customizations when they
need to open, create, or edit registry keys only if the target key is writable
inside the sandbox policy.

Before this SREV, `Key_OpenIfBoxed` rebuilt the registry path itself when
`OBJECT_ATTRIBUTES.RootDirectory` was present:

- it allocated a fixed `PAGE_SIZE` `KEY_NAME_INFORMATION` buffer;
- it called `NtQueryKey(KeyNameInformation)`;
- it appended a backslash and copied `ObjectName->Buffer` with `wcscpy`;
- it did not free the allocated buffer;
- it assumed both the returned `KEY_NAME_INFORMATION.Name` and the
  `UNICODE_STRING` object name could be consumed as NUL-terminated strings.

`Key_DeleteValueFromCLSID` also built
`\registry\machine\software\classes\<kind>\{<guid>}` in a fixed 128-WCHAR
temporary buffer and did not free it.

## Official Shape

- Microsoft documents `KEY_NAME_INFORMATION.NameLength` as the byte size of the
  key name, and documents `Name` as not NUL-terminated:
  `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntddk/ns-ntddk-_key_name_information`.
- Microsoft documents `ZwQueryKey` as returning required buffer size through
  `ResultLength` on `STATUS_BUFFER_OVERFLOW` or `STATUS_BUFFER_TOO_SMALL`:
  `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-zwquerykey`.
- Microsoft documents `OBJECT_ATTRIBUTES.ObjectName` as a `PUNICODE_STRING`,
  with `RootDirectory` making that name relative to the root object directory:
  `https://learn.microsoft.com/en-us/windows/win32/api/ntdef/ns-ntdef-_object_attributes`.

The legal external shape is counted strings plus optional root-relative object
names. A NUL-terminated string may be passed to `SbieDll_MatchPath` only after a
local owner has created that NUL-terminated projection.

## Schema

`KEY_UTIL_REGISTRY_PATH_SHAPE` says:

- `Key_GetName` owns key path normalization for
  `RootDirectory + UNICODE_STRING ObjectName`.
- `Key_OpenIfBoxed` must not create a second registry path builder from
  `KEY_NAME_INFORMATION`.
- `Key_OpenIfBoxed` must call `SbieDll_MatchPath` on the NUL-terminated true
  path returned by `Key_GetName`.
- `Key_OpenIfBoxed` must preserve the existing policy decision: any matched flag
  other than `PATH_WRITE_FLAG` blocks the helper with `STATUS_BAD_INITIAL_PC`.
- `Key_OpenOrCreateIfBoxed` saves and restores the security descriptor with the
  same pointer level as `OBJECT_ATTRIBUTES.SecurityDescriptor`.
- `Key_DeleteValueFromCLSID` must allocate storage from the measured prefix,
  class/id, GUID, braces, slash, and terminator, then free that storage before
  return.
- SREV-176 does not change the registry policy model, custom app behavior, CLSID
  value names, WOW64 access flags, or the create-on-missing behavior.
- Linux source gates are not Windows DLL build/runtime proof.

## Topology

Legal helper topology after this SREV:

```text
OBJECT_ATTRIBUTES
  -> Key_GetName owner
  -> NUL-terminated TruePath
  -> SbieDll_MatchPath('k')
  -> NtOpenKey or STATUS_BAD_INITIAL_PC

CLSID delete helper
  -> measured prefix/class/GUID path
  -> Key_OpenIfBoxed policy gate
  -> NtDeleteValueKey
  -> Dll_Free(path)
```

This also preserves the higher product coordinate recorded in
`docs/plan/sandboxie-isolation-coordinate.md`: selected host registry state may
be readable, but mutations are routed through the sandbox write policy and
custom exceptions should stay narrow.

## Logic Risk

The original helper mixed two string worlds. Windows returns counted registry
names, but the helper appended and matched them as NUL-terminated strings. A long
root key plus relative object name could write past the `PAGE_SIZE` buffer. A
non-NUL-terminated `UNICODE_STRING` could be over-read by `wcscpy`. Repeated
customization calls also leaked the temporary buffers.

The correct repair is not another private parser. `Key_GetName` already owns
the key-name topology, including root-relative object names, boxed-path
normalization, `\REGISTRY\USER\CURRENT` handling, duplicate backslash cleanup,
and NUL termination.

## Action

`Key_OpenIfBoxed` now calls `Key_GetName` and passes its true path to
`SbieDll_MatchPath`. The manual `NtQueryKey`/`KEY_NAME_INFORMATION` path builder
was removed.

`Key_OpenOrCreateIfBoxed` now saves `SecurityDescriptor` with the same pointer
level it restores.

`Key_DeleteValueFromCLSID` now measures the prefix, class/id, and GUID strings,
allocates the exact temporary buffer, builds the path with `Sbie_snwprintf`,
and frees the buffer before return.

## Verification

Source-level gates:

```bash
python3 docs/plan/check-srev-176.py
bash docs/plan/check-srev-176.sh
python3 docs/plan/check-core-coverage.py
```

Full closure matrix:

```bash
python3 docs/plan/check-srev-176.py &&
bash docs/plan/check-srev-176.sh &&
python3 docs/plan/check-core-coverage.py &&
for s in docs/plan/check-srev-0*.sh docs/plan/check-srev-1*.sh docs/plan/check-kpath-0*.sh; do bash "$s"; done &&
git diff --check
```

Runtime/build gate: Windows DLL build plus sandbox customization smoke for
DCOM/AppID/Shell CLSID helpers, including root-relative registry opens and
longer CLSID paths.
