---
kind: srev-ledger-entry
id: SREV-152
title: PStore Timestamp Map View Lifetime
status: patched-source-level-after-official-file-mapping-api-review-needs-windows-runtime-proof
owner: Sandboxie/core/dll/ipstore_impl.cpp
spec: docs/plan/srev-152-pstore-timestamp-map-view-lifetime.md
schema: docs/plan/srev-152-pstore-timestamp-map-view-lifetime.schema.json
checker: docs/plan/check-srev-152.py
runtime_gate: Windows PStore mapping success, failure, and leak proof
---

### SREV-152: PStore Timestamp Map View Lifetime

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official `CreateFileMapping` / `MapViewOfFile` / `UnmapViewOfFile` review; needs Windows PStore runtime proof |
| Evidence | `Sandboxie/core/dll/ipstore_impl.cpp` was the top unnamed reviewable core file after SREV-151. `IPStoreImpl` stores a named protected-storage timestamp view in `global_timestamp`, declared in `Sandboxie/core/dll/ipstore_impl.h`. Before this SREV, constructor code wrote `*global_timestamp` whenever it had created the section, even if `MapViewOfFile` failed and returned `NULL`. Destructor code closed the file mapping handle but never unmapped a successful view. |
| Data | `section`, `global_timestamp`, `_SectionName`, `CreateFileMapping`, `OpenFileMapping`, `MapViewOfFile`, `UnmapViewOfFile`, `IPStoreImpl::IPStoreImpl`, and `IPStoreImpl::~IPStoreImpl`. |
| Schema | `PSTORE_TIMESTAMP_MAP_VIEW_LIFETIME` says `section` is a file mapping object handle, `global_timestamp` is a mapped view address returned by `MapViewOfFile`, `MapViewOfFile` may fail and return `NULL`, `global_timestamp` may be dereferenced only after a non-null check, successful mapped views must be unmapped with `UnmapViewOfFile`, and closing the mapping handle does not replace unmapping the view. |
| Topology | Legal flow is open/create mapping handle, map view to `global_timestamp` or `NULL`, write the initial timestamp only if the view is non-null, let read/write paths require `global_timestamp`, then destructor unmaps the view before closing `section`. |
| Logic Risk | Mapping handle success does not prove mapped-view success. The previous code crossed from handle state to pointer dereference without a pointer gate, and crossed from handle cleanup to view cleanup without calling the mapped-view owner API. |
| Official Shape | `docs/plan/srev-152-pstore-timestamp-map-view-lifetime.md` records Microsoft `CreateFileMapping`, `MapViewOfFile`, and `UnmapViewOfFile` references. `docs/plan/srev-152-pstore-timestamp-map-view-lifetime.schema.json` records the JSON Schema draft-07 local `PSTORE_TIMESTAMP_MAP_VIEW_LIFETIME` contract. |
| Fix | `IPStoreImpl::IPStoreImpl` now initializes the shared timestamp only when `MapViewOfFile` returned a non-null `global_timestamp`. `IPStoreImpl::~IPStoreImpl` now calls `UnmapViewOfFile(global_timestamp)` before closing the section handle. |
| Acceptance Gate | `docs/plan/check-srev-152.py` validates the draft-07 schema, official references, constructor non-null map-view gate, destructor unmap-before-close order, unchanged shared timestamp read/write topology, and the ledger fragment; `docs/plan/check-srev-152.sh` is the matrix wrapper. Runtime/build gate: Windows DLL build; PStore creation/open smoke proving timestamp mapping works when `MapViewOfFile` succeeds; fault injection or low resource smoke proving `MapViewOfFile` failure does not dereference `NULL`; leak observation proving `UnmapViewOfFile` runs before the mapping handle is closed. |
