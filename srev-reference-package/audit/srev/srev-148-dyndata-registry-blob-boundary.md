# SREV-148: DynData Registry Blob Boundary

## Stage Gate

| Field | Value |
|---|---|
| Stage | action |
| Input artifact | `Sandboxie/core/drv/dyn_data.c`, `Sandboxie/core/drv/dyn_data.h`, Microsoft `ZwQueryValueKey` and `KEY_VALUE_PARTIAL_INFORMATION` references |
| Output artifact | `docs/plan/srev-148-dyndata-registry-blob-boundary.schema.json`, `docs/plan/check-srev-148.py`, `docs/plan/check-srev-148.sh`, ledger fragment |
| Owner | driver-side dynamic OS offset table loader |
| Acceptance gate | source checker plus full SREV/KPATH/core coverage matrix; Windows driver build/runtime proof remains required |

## Evidence

`Sandboxie/core/drv/dyn_data.c` became the top unnamed reviewable core file after
SREV-147. It owns the dynamic OS offset table that feeds private kernel offsets
into token, thread, GUI clipboard, and syscall paths through `Dyndata_Config`.

The loader reads optional registry binary data `DynData` through `GetRegValue`.
`GetRegValue` copies the registry value's counted `KEY_VALUE_PARTIAL_INFORMATION`
`Data` bytes into a pool buffer and returns the byte count as `CustomSize`.
Before this SREV, `Dyndata_LoadData` read `Custom->Format`, `Custom->Signature`,
`Custom->Arch`, `Custom->Version`, `Dyndata->Count`, `Dyndata->Configs[Index]`,
and `Data->OsBuild_*` without first proving that the counted blob contained the
`SBIE_DYNDATA` header, the config-offset array, and the pointed-to
`SBIE_DYNCONFIG` entries. The old per-entry guard only checked whether
`Data > base + DyndataSize`, which still allowed equality, partial entries, and
offset-table overlap.

`Dyndata_InitDefault` also allocated the built-in table and called `memset` on
the returned pointer before checking whether `Pool_Alloc` succeeded.

Official references:

- https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-zwqueryvaluekey
- https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/ns-wdm-_key_value_partial_information

## Data

`DynData`, `DynDataSig`, `GetRegValue`, `KEY_VALUE_PARTIAL_INFORMATION.Data`,
`CustomSize`, `DefaultSize`, `SBIE_DYNDATA`, `SBIE_DYNCONFIG`, `Configs[]`,
`Size`, `Count`, `Dyndata_Config`, `Dyndata_Active`, `Dyndata_InitDefault`, and
`Dyndata_LoadData`.

## Schema

`DYNDATA_REGISTRY_BLOB_BOUNDARY` says:

- `GetRegValue` returns counted registry bytes; those bytes are not a legal
  `SBIE_DYNDATA` table until the local table shape is validated.
- The table must contain the fixed `SBIE_DYNDATA` header before any header field
  read.
- The `Configs` offset array must fit inside the counted blob before iteration.
- Each nonzero config offset must start after the offset array and its
  `Dyndata->Size` bytes must fit inside the counted blob without overflow.
- `Dyndata->Size` must be at least the current `SBIE_DYNCONFIG` size before the
  current driver reads current fields such as `OsBuild_min` and `OsBuild_max`.
- Built-in default table allocation must be checked before clearing or writing
  the allocated buffer.

## Topology

Legal dynamic data flow:

```text
registry value DynData
  -> GetRegValue counted byte buffer plus CustomSize
  -> Dyndata_IsValidData proves SBIE_DYNDATA header/config/entry ranges
  -> architecture/signature/version selection
  -> OS build match over in-bounds SBIE_DYNCONFIG entries
  -> bounded copy into Dyndata_Config
  -> token/thread/gui/syscall consumers read Dyndata_Config only when Dyndata_Active
```

## Logic Risk

`DynData` is a registry-provided binary blob. In test-signing mode it can bypass
signature verification, and even signed or corrupted data still needs a local
shape check before the kernel reads it as structures. A malformed `Count`,
`Size`, or offset entry could make the driver read outside the registry value
buffer while selecting an OS-build entry. A failed built-in table allocation
could also crash before the function returns `STATUS_INSUFFICIENT_RESOURCES`.

## Fix

`dyn_data.c` now has `Dyndata_IsValidData`, which verifies the counted table
header, nonzero count, minimum entry size, offset-array extent, each nonzero
entry offset, overflow, and entry end bound. Custom `DynData` is validated before
any header field is used, and the selected table is validated before OS-build
iteration. The stale `Data > base + size` check is removed because the helper
proves full-entry containment. `INIT_DATA` now checks `Pool_Alloc` before
calling `memset`.

## Acceptance Gate

`docs/plan/check-srev-148.py` validates the draft-07 schema, official
references, source helper, allocation ordering, custom-data validation before
header reads, selected-table validation before iteration, stale one-sided range
check removal, and the ledger fragment. `docs/plan/check-srev-148.sh` is the
matrix wrapper.

Runtime/build gate: Windows driver build; default Dyndata selection still works
on supported builds; malformed short `DynData`, truncated config arrays,
overlapping offsets, and partial entries fail closed with `Dyndata_Active=FALSE`
and log `MSG_1205` or `MSG_1206`; valid newer signed DynData still selects the
matching OS-build entry.
