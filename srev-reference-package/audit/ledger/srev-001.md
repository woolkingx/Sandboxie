---
kind: srev-ledger-entry
id: SREV-001
title: Dummy Directory Merge Uses Unbounded Fixed Buffer
status: patched-source-level-after-official-spec-analysis-needs-windows-runtime-proof
owner: "Sandboxie/core/dll/file_dir.c:1382"
spec: docs/plan/srev-001-directory-info-spec.md
schema: docs/plan/srev-001-directory-info-spec.schema.json
checker: docs/plan/check-srev-001.sh
runtime_gate: create many matching open/readable path rules and verify directory enumeration does not crash or corrupt
---
### SREV-001: Dummy Directory Merge Uses Unbounded Fixed Buffer

| Field | Content |
|---|---|
| Severity | [blocker] |
| Status | patched source-level after official spec analysis; needs Windows runtime proof |
| Evidence | `Sandboxie/core/dll/file_dir.c:1382` allocated a fixed `0x10000` `info_area`; `file_dir.c:1403-1486` appended dummy `FILE_ID_BOTH_DIR_INFORMATION` entries without tracking remaining bytes; the source comment said `possible info_area buffer overflow`. |
| Data | Directory information records with `FileNameLength` measured in bytes. |
| Schema | `FILE_ID_BOTH_DIR_INFORMATION.FileNameLength` is a byte count; the variable-size record must fit in the destination buffer and keep `NextEntryOffset` aligned. |
| Topology | Configured readable/open file paths are projected into a synthetic directory listing inside the hooked DLL. |
| Logic Risk | Many or long path rules could overwrite the pool-backed `info_area` before the synthetic listing is converted into `FILE_MERGE_CACHE_FILE` records. |
| Official Shape | `docs/plan/srev-001-directory-info-spec.md` records Microsoft/FSCC shape: `FileNameLength` is bytes, `NextEntryOffset` is bytes, multi-record buffers are 8-byte aligned, and `FileName` is variable payload rather than a null-terminated string contract. |
| Fix | `File_MergeDummy` now computes record size from `FIELD_OFFSET(FILE_ID_BOTH_DIR_INFORMATION, FileName) + FileNameLength`, aligns the next offset once, checks remaining `info_area` capacity before writing, and stops adding entries when full. It no longer writes `FileName[FileNameLength]`. |
| Acceptance Gate | `docs/plan/check-srev-001.sh` proves the source no longer uses `FileNameLength` as a WCHAR index and checks capacity before advancing `info_ptr`. Windows gate: create many matching open/readable path rules and verify directory enumeration does not crash or corrupt. |
