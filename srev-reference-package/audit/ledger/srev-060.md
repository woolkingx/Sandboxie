---
kind: srev-ledger-entry
id: SREV-060
title: File Snapshot Relocation Copy Path Gate
status: patched-source-level-after-official-wide-string-ntstatus-shape-and-local-file-ge
owner: Sandboxie/core/dll/file_snapshots.c
spec: docs/plan/srev-060-file-snapshot-relocation-copy-path.md
schema: docs/plan/srev-060-file-snapshot-relocation-copy-path.schema.json
checker: docs/plan/check-srev-060.py
runtime_gate: valid snapshot relocation preserves lookup/merge behavior; malformed or unmappable relocation avoids null dereference and avoids parent snapshot lookup with stale copy path
---
### SREV-060: File Snapshot Relocation Copy Path Gate

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official wide-string/NTSTATUS shape and local `File_GetName` output initialization analysis; needs Windows snapshot relocation runtime proof |
| Evidence | `Sandboxie/core/dll/file_snapshots.c` `File_GetPathFlagsEx` and `Sandboxie/core/dll/file_dir.c` directory merge both update a copy path after snapshot relocation by calling `File_GetName(NULL, &objname, &TruePath2, &CopyPath2, NULL)`. Both call sites ignored the returned `NTSTATUS` and immediately passed `CopyPath2` to `wcslen`/`wcscpy`. `File_GetName` initializes `*OutTruePath` and `*OutCopyPath` to `NULL` before conversion, so a failed relocation conversion can leave `CopyPath2 == NULL`. |
| Data | Relocated true path, `File_GetName` status, `TruePath2`, `CopyPath2`, current `CopyPath`, and parent snapshot lookup/merge continuation state. |
| Schema | `FILE_SNAPSHOT_RELOCATION_COPY_PATH` says `CopyPath2` may be used as a null-terminated source string only after `NT_SUCCESS(status)` and non-null output proof. Snapshot lookup must not continue with a stale previous `CopyPath` after relocation conversion failure. Directory merge must stop parent snapshot traversal if a relocation cannot produce a legal copy path. |
| Topology | Relocation true path flows through `File_GetName`, which owns true-to-copy path conversion. Only a proven converted copy path may cross into parent snapshot lookup or merge. |
| Logic Risk | A snapshot relocation failure should degrade lookup/merge state, not crash in `wcslen(NULL)` or merge the wrong parent snapshot using an older copy path. |
| Official Shape | `docs/plan/srev-060-file-snapshot-relocation-copy-path.md` records Microsoft `wcslen`, wide-string copy, and `NT_SUCCESS` references. `docs/plan/srev-060-file-snapshot-relocation-copy-path.schema.json` records the JSON Schema draft-07 local `FILE_SNAPSHOT_RELOCATION_COPY_PATH` contract. |
| Fix | `File_GetPathFlagsEx` now initializes `TruePath2`/`CopyPath2`, checks `NT_SUCCESS(status) && CopyPath2`, and clears `CopyPath` when relocation cannot be converted. The directory merge path now initializes `TruePath2`/`CopyPath2`, checks `NT_SUCCESS(status) && CopyPath2`, and stops parent snapshot traversal on conversion failure. |
| Acceptance Gate | `docs/plan/check-srev-060.py` validates the draft-07 schema, official references, `File_GetName` null-output shape, both caller gates, stale-copy-path prevention, and ledger entry; `docs/plan/check-srev-060.sh` is the matrix wrapper. Windows gate: valid snapshot relocation preserves lookup/merge behavior; malformed or unmappable relocation avoids null dereference and avoids parent snapshot lookup with stale copy path. |
