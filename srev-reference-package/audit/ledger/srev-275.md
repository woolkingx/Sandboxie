---
kind: srev-ledger-entry
id: SREV-275
title: File Rename Cross-Volume Gate
status: patched-comment-topology-after-official-rename-cross-volume-review-no-behavior-change
owner: Sandboxie/core/dll/file.c and Sandboxie/core/drv/file.c
spec: docs/plan/srev-275-file-rename-cross-volume-gate.md
schema: docs/plan/srev-275-file-rename-cross-volume-gate.schema.json
checker: docs/plan/check-srev-275.py
runtime_gate: Windows rename and MoveFileEx cross-volume matrix
---

### SREV-275: File Rename Cross-Volume Gate

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | patched comment/topology after official rename cross-volume review; no behavior change |
| Evidence | `File_RenameOpenFile` and `File_RenameFile` call `__sys_NtSetInformationFile(..., FileRenameInformation)`, and `File_Api_Rename` calls `ZwSetInformationFile(..., FileRenameInformation)` through the driver API rename path. All three carried FIXME comments about possible `STATUS_NOT_SAME_DEVICE`. Official `FILE_RENAME_INFORMATION` rules make that status a legal same-volume boundary, not a local oddity to hide. |
| Data | `File_RenameOpenFile`, `File_RenameFile`, `File_Api_Rename`, `API_RENAME_FILE_ARGS`, `FILE_RENAME_INFORMATION`, `RootDirectory`, `FileNameLength`, `FileRenameInformation`, `FileLinkInformation`, `__sys_NtSetInformationFile`, `ZwSetInformationFile`, `STATUS_SHARING_VIOLATION`, `STATUS_NOT_SAME_DEVICE`, `MoveFileEx`, and `MOVEFILE_COPY_ALLOWED`. |
| Schema | `FILE_RENAME_CROSS_VOLUME_GATE` says `FILE_RENAME_INFORMATION` is the concrete buffer for `FileRenameInformation`; NT file rename is a same-volume operation; `STATUS_NOT_SAME_DEVICE` is the legal NT result for cross-volume rename targets; `MoveFileEx` with `MOVEFILE_COPY_ALLOWED` is the Win32 copy/delete fallback owner for cross-volume moves; Sandboxie's NT rename hook and driver API rename preserve cross-volume failure rather than inventing copy/delete policy; sharing-violation retry in `File_RenameFile` remains unchanged; this SREV changes comments and proof only. |
| Topology | `Win32 MoveFileEx / caller policy -> optional MOVEFILE_COPY_ALLOWED -> NtSetInformationFile(FileRenameInformation) -> NT same-volume rename gate -> STATUS_NOT_SAME_DEVICE if target crosses a volume`. `File_RenameOpenFile` projects an open-path target parent through `RootDirectory`; `File_RenameFile` projects source/target true and copy paths before issuing `FileRenameInformation` or `FileLinkInformation`; `File_Api_Rename` projects `API_RENAME_FILE` counted target path/name through a target-parent `RootDirectory` and issues `ZwSetInformationFile(FileRenameInformation)` on a kernel handle reopened from the caller file object. |
| Logic Risk | Treating `STATUS_NOT_SAME_DEVICE` as a bug inside the NT rename hook would move copy/delete behavior into the wrong layer. That would duplicate Win32 policy, blur rename versus copy semantics, and change security descriptor / ACL inheritance behavior for cross-volume moves. |
| Official Shape | Microsoft documents `FILE_RENAME_INFORMATION` rename rules as same-volume only. Microsoft documents `NtSetInformationFile` as selecting the `FileInformation` structure by `FileInformationClass`. Microsoft documents `FltSetInformationFile` callers as responsible for ensuring a rename target is on the same volume. Microsoft documents `MoveFileEx(MOVEFILE_COPY_ALLOWED)` as the Win32 layer that can simulate a cross-volume move by copying and deleting. |
| Fix | Comment-only source clarification. All three FIXME blocks now name SREV-275 and state that `FILE_RENAME_INFORMATION` is an NT same-volume operation. The hook and driver API preserve `STATUS_NOT_SAME_DEVICE` so the caller or Win32 layer can decide whether to use copy/delete fallback. No behavior changed. |
| Acceptance Gate | `docs/plan/check-srev-275.py` validates the draft-07 schema, official references, all three source comment owners, `File_RenameOpenFile`, `File_RenameFile`, and `File_Api_Rename` rename issue sites, sharing retry preservation, stale FIXME removal, `MOVEFILE_COPY_ALLOWED` boundary documentation, and ledger fragment; `docs/plan/check-srev-275.sh` is the targeted wrapper. Runtime gate: Windows rename/move matrix covering same-directory rename, same-volume cross-directory rename, open-path target rename, cross-volume rename returning `STATUS_NOT_SAME_DEVICE`, and Win32 `MoveFileEx` with and without `MOVEFILE_COPY_ALLOWED`. |
