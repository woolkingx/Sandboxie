# SREV-037: IPC Create Directory Or Link Counted String

## Finding

`Sandboxie/core/drv/ipc.c` receives `API_CREATE_DIR_OR_LINK_ARGS.objname` and
optional `target` as user `UNICODE_STRING64*` values. The driver accepted odd
byte lengths by truncating them with `& ~1`, copied counted bytes into local
NUL-terminated buffers, then passed those buffers through `RtlInitUnicodeString`
for boxed-path checks and object creation. The successful handle path also
allocated `DIR_OBJ_HANDLE` and immediately wrote through it without proving the
allocation succeeded.

## Official Shape

- `UNICODE_STRING.Length` is a byte count; if a string is NUL-terminated,
  `Length` does not include the trailing NUL:
  `https://learn.microsoft.com/en-us/windows/win32/api/ntdef/ns-ntdef-_unicode_string`
- `RtlInitUnicodeString` initializes a counted Unicode string from a
  NUL-terminated source pointer:
  `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-rtlinitunicodestring`
- `ZwCreateDirectoryObject` returns a directory object handle through an output
  `PHANDLE`; once no longer used, the driver must close it:
  `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-zwcreatedirectoryobject`
- `IoCreateSymbolicLink` documents the symbolic-link boundary as two buffered
  Unicode strings, the symbolic-link name and target device name:
  `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-iocreatesymboliclink`

## Local Schema

Machine-readable schema:

```text
docs/plan/srev-037-ipc-create-dir-link-wire.schema.json
```

`objname` is required. `target` is optional: absent means create an object
directory, present means create a symbolic link. Both fields are counted WCHAR
byte strings from user mode. Legal input must be at least one WCHAR,
WCHAR-aligned, below the local 2048-byte cap, and not larger than
`MaximumLength`. Because the local topology gate uses `RtlInitUnicodeString`
before `Box_IsBoxedPath`, embedded NULs are rejected so the boxed path exactly
matches the copied payload.

The IPC bootstrap has one narrow local topology exception: `Ipc_CreateObjects`
uses a same-box `BNOLINKS` auxiliary subtree next to the configured session IPC
root to build the BaseNamedObjects `Global` / `Local` / `Session` link
topology. `Ipc_Api_CreateDirOrLink` therefore accepts either the configured
boxed IPC root or that exact same-box `BNOLINKS` subtree. It must not accept any
other sibling path under the box parent.

## Fix

`Ipc_Api_CreateDirOrLink` now copies both strings through a local helper that
validates counted byte shape, rejects embedded NULs, and returns a local
NUL-terminated kernel buffer. Odd byte lengths are rejected instead of silently
truncated. The successful handle path now checks `DIR_OBJ_HANDLE` allocation;
if tracking allocation fails, the newly created handle is closed and the API
returns `STATUS_INSUFFICIENT_RESOURCES`.

The boxed-path gate now routes through a local helper that preserves the normal
IPC-root check and adds only the same-box `BNOLINKS` bootstrap subtree needed by
`Ipc_CreateObjects`.

## Acceptance Gate

`docs/plan/check-srev-037.py` validates the local schema, official references,
source counted-string helper, removal of `Length & ~1` in this API path, boxed
path topology checks, and handle cleanup on tracking allocation failure.

Windows gate still needed: sandboxed create-directory and create-symbolic-link
paths, malformed odd-length and embedded-NUL strings, target outside the box,
and simulated tracking allocation failure should preserve handle ownership.
