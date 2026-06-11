---
kind: srev-ledger-entry
id: SREV-274
title: File Hard-Link Class Boundary
status: patched-comment-topology-after-official-hard-link-information-class-review-no-behavior-change
owner: Sandboxie/core/dll/file.c
spec: docs/plan/srev-274-file-hard-link-class-boundary.md
schema: docs/plan/srev-274-file-hard-link-class-boundary.schema.json
checker: docs/plan/check-srev-274.py
runtime_gate: Windows hard-link set-information class matrix
---

### SREV-274: File Hard-Link Class Boundary

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | patched comment/topology after official hard-link information-class review; no behavior change |
| Evidence | `File_NtSetInformationFile` routes `FileLinkInformation` and `FileLinkInformationEx` into `File_RenameFile(..., TRUE)`, but leaves `FileHardLinkInformation` and `FileHardLinkFullIdInformation` in a native `__sys_NtSetInformationFile` compatibility probe. The branch carried a bare `else // todo`, hiding the reason these classes are not merged into the local create-hard-link path. |
| Data | `File_NtSetInformationFile`, `FileInformationClass`, `FileInformation`, `Length`, `FileLinkInformation`, `FileLinkInformationEx`, `FileHardLinkInformation`, `FileHardLinkFullIdInformation`, `File_RenameFile`, `__sys_NtSetInformationFile`, `STATUS_INVALID_DEVICE_REQUEST`, and `Sandboxie/core/drv/file_flt.c` `IRP_MJ_SET_INFORMATION` hard-link handling. |
| Schema | `FILE_HARD_LINK_CLASS_BOUNDARY` says `NtSetInformationFile` `FileInformation` buffer shape is determined by `FileInformationClass`; `FileLinkInformation` creates a hard link with `FILE_LINK_INFORMATION`; `FileLinkInformationEx` uses the `FILE_LINK_INFORMATION` `Flags` union shape; only `FileLinkInformation` and `FileLinkInformationEx` are routed into `File_RenameFile` hard-link creation; `FileHardLinkInformation` and `FileHardLinkFullIdInformation` remain native compatibility probes until a class-specific setter contract is proven; failed alternate probes return `STATUS_INVALID_DEVICE_REQUEST`; `file_flt.c` denies alternate hard-link classes for sandboxed `IRP_MJ_SET_INFORMATION`; this SREV changes comments and proof only. |
| Topology | `NtSetInformationFile -> FileInformationClass -> FileLinkInformation/Ex -> File_RenameFile(..., TRUE) -> copy-path-aware hard-link creation`; alternate hard-link classes route to native probe and failure fallback, while the minifilter adjacency denies those alternate classes for sandboxed set-information requests. |
| Logic Risk | The stale todo could lead a future patch to combine all hard-link-named classes into one parser. That would be schema-wrong unless the alternate setter shape, length gate, root-directory handling, and minifilter topology are proven from official and runtime evidence. |
| Official Shape | Microsoft documents `NtSetInformationFile` as selecting the concrete `FileInformation` structure by `FileInformationClass`; `FileLinkInformation` creates a hard link using `FILE_LINK_INFORMATION`; `FILE_LINK_INFORMATION` carries `ReplaceIfExists` for `FileLinkInformation` and `Flags` for `FileLinkInformationEx`; `NtQueryInformationFile(FileHardLinkInformation)` returns `FILE_LINKS_INFORMATION`, a list-style links buffer. |
| Fix | Comment-only source clarification. The bare `else // todo` now names SREV-274 and says only `FileLinkInformation` / `FileLinkInformationEx` have the local `FILE_LINK_INFORMATION` create-hard-link path. Alternate hard-link classes remain native compatibility probes until a class-specific setter contract is proven. No behavior changed. |
| Acceptance Gate | `docs/plan/check-srev-274.py` validates the draft-07 schema, official references, `File_NtSetInformationFile` hard-link class routing, native compatibility probe preservation, `STATUS_INVALID_DEVICE_REQUEST` fallback, driver minifilter denial adjacency, stale todo removal, and ledger fragment; `docs/plan/check-srev-274.sh` is the targeted wrapper. Runtime gate: Windows hard-link set-information matrix covering `FileLinkInformation`, `FileLinkInformationEx`, `FileHardLinkInformation`, and `FileHardLinkFullIdInformation`, with sandboxed inside-box, outside-box, cross-volume, existing-target, and caller fallback behavior. |
