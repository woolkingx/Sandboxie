# SREV-213: Registry Delete V2 Counted Value Name

## Stage

schema -> boundary -> topology -> logic -> action -> verify

## Evidence

`Sandboxie/core/dll/key_del.c` was the top unnamed reviewable core file after
SREV-212. It owns the registry delete-v2 marker tree persisted in
`RegPaths.dat`. Keys are recorded by their true registry path. Deleted values
are recorded by appending `\$` and the value name to the key path.

The caller in `Sandboxie/core/dll/key.c` receives value names from
`NtDeleteValueKey`, `NtQueryValueKey`, and `NtEnumerateValueKey`. These API
surfaces use counted names: `NtDeleteValueKey` receives a `UNICODE_STRING`,
and registry value information structures carry `NameLength` plus inline name
bytes. Before this fix, delete-v2 passed `ValueName->Buffer` and inline
`KEY_VALUE_*_INFORMATION.Name` fields to helpers that used `wcslen` /
`wcscat`, treating counted buffers as null-terminated strings.

## Data

`key_del.c`, `key.c`, `Key_MarkDeletedEx_v2`, `Key_IsDeletedEx_v2`,
`Key_IsDeletedExLen_v2`, `NtDeleteValueKey`, `UNICODE_STRING.ValueName`,
`KEY_VALUE_BASIC_INFORMATION.NameLength`, `KEY_VALUE_FULL_INFORMATION.NameLength`,
`RegPaths.dat`, `KEY_DELETED_FLAG`, `KEY_CHILDREN_DELETED_FLAG`,
`File_MarkDeleted_internal`, and `File_GetPathFlags_internal`.

## Official Shape

Microsoft documents `ZwDeleteValueKey` as receiving the value name through a
`PUNICODE_STRING`. `UNICODE_STRING.Length` is a byte count and does not include
a terminating null if one exists; returned counted string buffers might not be
null-terminated.

Microsoft documents `KEY_VALUE_BASIC_INFORMATION` and
`KEY_VALUE_FULL_INFORMATION` as carrying `NameLength` plus an inline `Name`
array. The documented shape is counted-name data, not a guaranteed
null-terminated string.

References:

- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-zwdeletevaluekey`
- `https://learn.microsoft.com/en-us/windows/win32/api/subauth/ns-subauth-unicode_string`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/ns-wdm-_key_value_basic_information`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/ns-wdm-_key_value_full_information`

## Schema

`REG_DELETE_V2_COUNTED_VALUE_NAME` says:

- `key_del.c` owns delete-v2 marker path construction.
- Value names crossing from `NtDeleteValueKey` are counted
  `UNICODE_STRING` buffers.
- Value names crossing from registry enumeration/query information structures
  are counted by `NameLength`.
- Delete-v2 marker helpers must copy exactly the counted value-name characters
  and then synthesize a local terminator for `RegPaths.dat` path lookup.
- Null-terminated generated merge names may still use the compatibility wrapper
  that measures with `wcslen`.
- Allocation failure while marking a deletion must return
  `STATUS_INSUFFICIENT_RESOURCES`; allocation failure while checking deletion
  status must fail closed to "not deleted" rather than over-reading.

## Topology

```text
NtDeleteValueKey(ValueName UNICODE_STRING)
-> Key_NtDeleteValueKey
-> Key_MarkDeletedEx_v2(TruePath, ValueName->Buffer, ValueName->Length / sizeof(WCHAR))
-> counted copy into local NUL-terminated marker path
-> File_MarkDeleted_internal(RegPaths.dat tree)
```

Enumeration/query check topology:

```text
KEY_VALUE_*_INFORMATION.Name + NameLength
-> Key_IsDeletedExLen_v2(TruePath, Name, NameLength / sizeof(WCHAR), TRUE)
-> counted copy into local NUL-terminated marker path
-> File_GetPathFlags_internal(RegPaths.dat tree)
```

## Logic Risk

Registry value names are not owned by C string APIs at the API boundary. A
value name buffer can be counted without a terminator, and enumeration result
names are explicitly represented by `NameLength`. Passing those buffers through
`wcslen` / `wcscat` can over-read past the API-provided buffer before the
delete marker is even applied.

## Fix

`Key_MarkDeletedEx_v2` now accepts the value-name character count and builds
the delete marker path with `wmemcpy`. `Key_IsDeletedExLen_v2` was added for
counted-name callers. The existing `Key_IsDeletedEx_v2` remains as a
null-terminated compatibility wrapper for generated merge names. Counted
callers in `key.c` now pass `ValueName->Length`, `ValueNameLen1`, or
`KEY_VALUE_*_INFORMATION.NameLength` instead of relying on `wcslen`.

## Acceptance Gate

`docs/plan/check-srev-213.py` validates the draft-07 schema, official
references, counted delete-marker construction in `key_del.c`, counted
call-site wiring in `key.c`, preservation of the null-terminated wrapper for
merge-generated names, split ledger fragment, and removal of the stale
`ValueName->Buffer` null-terminated delete-marker call.

Runtime/build gate: Windows DLL build plus registry delete-v2 smoke with value
names from `NtDeleteValueKey`, `NtQueryValueKey`, and `NtEnumerateValueKey`,
including a non-null-terminated counted test name, proving deleted values are
hidden without over-reading and generated merge names still match.
