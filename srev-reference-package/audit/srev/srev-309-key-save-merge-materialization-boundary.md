# SREV-309: Key Save Merge Materialization Boundary

## Stage Gate

| Field | Value |
|---|---|
| Stage | data -> schema -> topology -> logic -> verify |
| Input artifact | `Sandboxie/core/dll/key.c`, Microsoft `RegSaveKey` / `RegSaveKeyEx` and registry enumeration/value documentation |
| Output artifact | Registry save versus Sandboxie merge-view materialization boundary, draft-07 schema, targeted checker, ledger fragment |
| Owner | `Key_NtSaveKey` / `Key_NtSaveKeyEx` |
| Acceptance gate | Targeted checker validates source comment ownership, unchanged native save calls, official references, merge/enumeration adjacency, stale TODO removal, combined ledger, and ledger fragment |

## Data

`Key_NtSaveKey` and `Key_NtSaveKeyEx` currently log `MSG_2205` and then call the
native save functions directly:

```text
Key_NtSaveKey(KeyHandle, FileHandle)
  -> SbieApi_Log(2205, "NtSaveKey")
  -> __sys_NtSaveKey(KeyHandle, FileHandle)

Key_NtSaveKeyEx(KeyHandle, FileHandle, Flags)
  -> SbieApi_Log(2205, "NtSaveKeyEx")
  -> __sys_NtSaveKeyEx(KeyHandle, FileHandle, Flags)
```

The old comments said to copy all registry keys from host to box for the used
`KeyHandle` so everything would be saved. That identifies a real topology gap:
Sandboxie exposes a merged registry view through `Key_Merge`,
`Key_NtEnumerateKey`, `Key_NtEnumerateValueKey`, `Key_NtQueryValueKey`, and
related helpers, but `NtSaveKey` / `NtSaveKeyEx` save the physical key tree
behind the handle. The virtual merge view is not automatically materialized into
the box tree before saving.

## Official Shape

Microsoft documents `RegSaveKeyW` as saving a specified key and all of its
subkeys and values to a new file. The `hKey` handle identifies the open key to
save. Microsoft documents `RegSaveKeyEx` as the extended save operation with a
`Flags` parameter selecting save format.

Microsoft documents registry enumeration/value APIs as separate operations:
`ZwEnumerateKey` enumerates subkeys, `ZwEnumerateValueKey` enumerates value
entries, and `ZwQueryValueKey` returns value data. Those are the shapes a
pre-save materializer would need to drive or emulate before changing save
behavior.

Official references:

- `https://learn.microsoft.com/en-us/windows/win32/api/winreg/nf-winreg-regsavekeyw`
- `https://learn.microsoft.com/en-us/windows/win32/api/winreg/nf-winreg-regsavekeyexa`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-zwenumeratekey`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-zwenumeratevaluekey`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-zwqueryvaluekey`

## Schema

Local schema:

```text
docs/plan/srev-309-key-save-merge-materialization-boundary.schema.json
```

Contract id:

```text
KEY_SAVE_MERGE_MATERIALIZATION_BOUNDARY
```

## Topology

Current save topology:

```text
caller KeyHandle
  -> Key_NtSaveKey / Key_NtSaveKeyEx
  -> native save
  -> physical registry tree behind KeyHandle
```

Sandboxie merged-read topology:

```text
caller KeyHandle
  -> Key_GetName
  -> TruePath + CopyPath
  -> Key_Merge
  -> merged subkey/value enumeration/query
```

Potential future materialization topology:

```text
caller KeyHandle
  -> prove TruePath/CopyPath and save target
  -> enumerate merged subkeys and values
  -> create/copy missing host-only nodes into box tree
  -> preserve delete markers and relocation semantics
  -> native save of box-visible tree
```

SREV-309 does not implement that topology. It records the boundary and runtime
gate needed before changing save behavior.

## Logic Risk

The old TODO describes a solution without naming the legal owner, API shape, or
runtime proof. Copying "all registry keys" before save is not a local one-line
fix: it crosses merge semantics, delete markers, relocation, value type/data
copying, security descriptors, virtualization policy, and native hive-save file
ownership.

The stable boundary for the current source is:

```text
native save sees physical key tree
Sandboxie merge view is virtual
materialization requires a separate proven topology
```

## Fix

The source comments now name SREV-309 and the physical-tree boundary for
`NtSaveKey` and `NtSaveKeyEx`. They explicitly state that the merged host+box
view is not materialized before native save, and that pre-save materialization
requires a Windows hive-save runtime gate before behavior changes.

No behavior changed: `SbieApi_Log(2205, ...)`, `__sys_NtSaveKey`, and
`__sys_NtSaveKeyEx` calls are unchanged. This is a comment-only source
classification and proof entry.

## Acceptance Gate

`docs/plan/check-srev-309.py` validates the draft-07 schema, official
references, source comment owner, unchanged native save calls, merge/enumeration
adjacency, stale TODO removal, combined ledger entry, and split ledger fragment.

Runtime gate: Windows hive-save smoke with keys that differ between host and
box trees, including host-only subkeys, box-only subkeys, deleted values,
relocated keys, multiple value types, and save-format flags for `NtSaveKeyEx`,
before any materialization behavior change.
