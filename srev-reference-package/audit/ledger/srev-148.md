---
kind: srev-ledger-entry
id: SREV-148
title: DynData Registry Blob Boundary
status: patched-source-level-after-official-registry-value-shape-review-needs-windows-runtime-proof
owner: Sandboxie/core/drv/dyn_data.c
spec: docs/plan/srev-148-dyndata-registry-blob-boundary.md
schema: docs/plan/srev-148-dyndata-registry-blob-boundary.schema.json
checker: docs/plan/check-srev-148.py
runtime_gate: Windows driver build and malformed DynData registry blob runtime proof
---

### SREV-148: DynData Registry Blob Boundary

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official `ZwQueryValueKey` / `KEY_VALUE_PARTIAL_INFORMATION` and local `SBIE_DYNDATA` schema review; needs Windows driver runtime proof |
| Evidence | `Sandboxie/core/drv/dyn_data.c` was the top unnamed reviewable core file after SREV-147. It owns the dynamic OS offset table consumed through `Dyndata_Config` by token, thread, GUI clipboard, and syscall paths. `Sandboxie/core/drv/dyn_data.h` defines the local `SBIE_DYNDATA` and `SBIE_DYNCONFIG` table schema. `GetRegValue` returns counted registry value bytes from `KEY_VALUE_PARTIAL_INFORMATION.Data` plus a byte count. Before this SREV, `Dyndata_LoadData` read `Custom->Format`, `Custom->Signature`, `Custom->Arch`, `Custom->Version`, `Dyndata->Count`, `Dyndata->Configs[Index]`, and `Data->OsBuild_*` before proving that the counted blob contained the local header, offset array, and pointed-to `SBIE_DYNCONFIG` entries. The old range guard only checked `Data > base + DyndataSize`, allowing equality and partial-entry cases. `Dyndata_InitDefault` also called `memset(Default)` before checking whether `Pool_Alloc` returned `NULL`. |
| Data | `DynData`, `DynDataSig`, `GetRegValue`, `KEY_VALUE_PARTIAL_INFORMATION.Data`, `CustomSize`, `DefaultSize`, `SBIE_DYNDATA`, `SBIE_DYNCONFIG`, `Configs[]`, `Size`, `Count`, `Dyndata_Config`, `Dyndata_Active`, `Dyndata_InitDefault`, and `Dyndata_LoadData`. |
| Schema | `DYNDATA_REGISTRY_BLOB_BOUNDARY` says registry bytes are not a legal `SBIE_DYNDATA` table until local shape validation proves the fixed header, offset-array extent, minimum current `SBIE_DYNCONFIG` size, each nonzero entry offset after the offset array, and each full entry range without overflow. Built-in table allocation must be checked before clearing or writing the buffer. |
| Topology | Legal flow is registry `DynData` counted bytes, `Dyndata_IsValidData` shape proof, architecture/signature/version selection, OS-build match over in-bounds config entries, bounded copy into `Dyndata_Config`, then consumers read `Dyndata_Config` only after `Dyndata_Active` is set. |
| Logic Risk | A malformed registry binary blob, especially under test-signing where signature verification can be skipped, could make the kernel read outside the value buffer while selecting offsets. A failed built-in table allocation could also crash before returning `STATUS_INSUFFICIENT_RESOURCES`. |
| Official Shape | `docs/plan/srev-148-dyndata-registry-blob-boundary.md` records Microsoft `ZwQueryValueKey` and `KEY_VALUE_PARTIAL_INFORMATION` references. `docs/plan/srev-148-dyndata-registry-blob-boundary.schema.json` records the JSON Schema draft-07 local `DYNDATA_REGISTRY_BLOB_BOUNDARY` contract. |
| Fix | `dyn_data.c` now validates `DynData` with `Dyndata_IsValidData` before using custom header fields, validates the selected table before iterating offsets, removes the stale one-sided `Data > base + size` check, and checks `Pool_Alloc` before `memset` in `INIT_DATA`. |
| Acceptance Gate | `docs/plan/check-srev-148.py` validates the draft-07 schema, official references, `dyn_data.h` local schema, source helper, allocation ordering, validation-before-read ordering, stale range-check removal, and the ledger fragment; `docs/plan/check-srev-148.sh` is the matrix wrapper. Runtime/build gate: Windows driver build; default Dyndata selection still works on supported builds; malformed short `DynData`, truncated config arrays, overlapping offsets, and partial entries fail closed with `Dyndata_Active=FALSE` and log `MSG_1205` or `MSG_1206`; valid newer signed DynData still selects the matching OS-build entry. |
