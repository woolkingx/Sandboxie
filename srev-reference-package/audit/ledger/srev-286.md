---
kind: srev-ledger-entry
id: SREV-286
title: Snapshot Path Builder TLS Gate
status: patched-source-level-after-srev-196-tls-buffer-and-official-wide-string-review-needs-windows-runtime
owner: Sandboxie/core/dll/file_snapshots.c
spec: docs/plan/srev-286-snapshot-path-builder-tls-gate.md
schema: docs/plan/srev-286-snapshot-path-builder-tls-gate.schema.json
checker: docs/plan/check-srev-286.py
runtime_gate: Windows snapshot matrix with active snapshot chain boxed copy path parent-snapshot hit prefix miss TMPL_NAME_BUFFER allocation failure injection relocation refresh and File_Delete_v2 true false
---

### SREV-286: Snapshot Path Builder TLS Gate

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after SREV-196 TLS buffer and official wide-string review; needs Windows runtime proof |
| Evidence | `File_MakeSnapshotPath` allocated `TMPL_NAME_BUFFER` with `Dll_GetTlsNameBuffer` and immediately passed `TmplName` to `wcsncpy` and `wcscpy`. Callers already checked a null builder result, but the builder itself could write to the failed allocation before returning null. SREV-196 proves `Dll_GetTlsNameBuffer` can return null on allocation failure. |
| Data | `Cur_Snapshot`, `CopyPath`, `File_FindBoxPrefix(CopyPath)`, `TMPL_NAME_BUFFER`, `TmplName`, `File_Snapshot_Prefix`, `Cur_Snapshot->ID`, `File_GetPathFlagsEx`, and `File_FindSnapshotPath`. |
| Schema | `SNAPSHOT_PATH_BUILDER_TLS_GATE` says `File_MakeSnapshotPath` owns snapshot path assembly into `TMPL_NAME_BUFFER`; `Dll_GetTlsNameBuffer` output must be checked before `wcsncpy` or `wcscpy` writes into it; `Cur_Snapshot` null and missing boxed prefix remain fail-closed builder inputs; callers may use the snapshot path only after the builder returns non-null; SREV-196 owns the local TLS name-buffer allocation failure contract; SREV-060 owns snapshot relocation copy-path conversion before this builder; this SREV does not change snapshot traversal, relocation policy, prefix selection, or `File_Delete_v2` behavior. |
| Topology | `File_GetPathFlagsEx / File_FindSnapshotPath -> File_MakeSnapshotPath -> File_FindBoxPrefix -> Dll_GetTlsNameBuffer(TMPL_NAME_BUFFER) -> non-null gate -> wcsncpy/wcscpy path assembly -> caller RtlInitUnicodeString/File_GetFileType`. |
| Logic Risk | The caller-side null check hid the missing owner-local gate. Under allocation pressure, a missing temporary snapshot path buffer could become a null destination write before caller stop logic ran. |
| Official Shape | Microsoft documents `wcscpy` as copying a null-terminated source into a destination with no error return reserved and no destination-size check. Microsoft documents `wcsncpy` as copying a caller-provided count from source to destination. Both require a valid destination buffer. |
| Fix | `File_MakeSnapshotPath` now returns null immediately if `Dll_GetTlsNameBuffer(... TMPL_NAME_BUFFER ...)` fails. `File_GetPathFlagsEx` keeps the same stop behavior and uses an owner-tagged SREV-286 comment. |
| Acceptance Gate | `docs/plan/check-srev-286.py` validates the draft-07 schema, official references, SREV-196/SREV-060 adjacency, the builder null gate before the first `wcsncpy` write, both caller stop gates, stale source comment removal, combined ledger entry, and split ledger fragment; `docs/plan/check-srev-286.sh` is the targeted wrapper. Runtime gate: Windows snapshot matrix with active snapshot chain, boxed copy path, parent-snapshot hit, prefix miss, TLS allocation failure injection for `TMPL_NAME_BUFFER`, relocation refresh, and `File_Delete_v2` true/false. |
