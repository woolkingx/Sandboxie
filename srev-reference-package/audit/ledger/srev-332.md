---
kind: srev-ledger-entry
id: SREV-332
title: File Filter ParentOfTarget Context
status: patched-comment-topology-after-official-parent-target-context-review-no-behavior-change
owner: Sandboxie/core/drv/file_flt.c
spec: docs/plan/srev-332-file-flt-parent-target-context.md
schema: docs/plan/srev-332-file-flt-parent-target-context.schema.json
checker: docs/plan/check-srev-332.py
runtime_gate: Windows rename/link matrix for ParentOfTarget context and RelatedFileObject fallback
---

### SREV-332: File Filter ParentOfTarget Context

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | patched comment/topology after official ParentOfTarget context review; no behavior change |
| Evidence | `File_PreOperation` had a disabled alternative check that tried to inspect `Iopb->Parameters.SetFileInformation.ParentOfTarget->FileName` directly and noted that it lacked a device path. The active route sends link and rename set-information classes into `File_RenameOperation`, which requires `ParentOfTarget`, validates the counted target name, optionally replaces a relative parent file object with `RelatedFileObject`, and then calls `File_Generic_MyParseProc` with `IO_OPEN_TARGET_DIRECTORY`. |
| Data | `IRP_MJ_SET_INFORMATION`, `FLT_PARAMETERS.SetFileInformation.ParentOfTarget`, `InfoBuffer`, `FileLinkInformation`, `FileLinkInformationEx`, `FileRenameInformation`, `FileRenameInformationEx`, `FILE_LINK_INFORMATION.FileNameLength`, `FILE_RENAME_INFORMATION.FileNameLength`, `RelatedFileObject`, `File_Generic_MyParseProc`, and `IO_OPEN_TARGET_DIRECTORY`. |
| Schema | `FILE_FLT_PARENT_TARGET_CONTEXT` says `ParentOfTarget` is a file object pointer carrier for rename/link target parent context; `ParentOfTarget->FileName` is not the full target path owner by itself; `File_RenameOperation` combines `ParentOfTarget` context with the counted target `FileName` before policy parsing; `RelatedFileObject` full-path fallback remains the local topology for relative parent file-object names; SREV-019 length gates remain the counted target-name proof before `UNICODE_STRING` construction; this SREV changes comments and proof only. |
| Topology | `File_PreOperation -> FileLinkInformation/FileLinkInformationEx -> File_RenameOperation(..., TRUE)` and `File_PreOperation -> FileRenameInformation/FileRenameInformationEx -> File_RenameOperation(..., FALSE)`. `File_RenameOperation -> ParentOfTarget file object -> FILE_*_INFORMATION.FileName counted target name -> optional RelatedFileObject full-path context -> File_Generic_MyParseProc(..., IO_OPEN_TARGET_DIRECTORY)`. |
| Logic Risk | The stale disabled comment framed the problem as a missing string prefix on `ParentOfTarget->FileName`. The correct shape is object context plus counted target name. A future direct string check against `ParentOfTarget->FileName` alone could evaluate a different path than the filesystem operation. |
| Official Shape | Microsoft documents `FLT_PARAMETERS.SetFileInformation.ParentOfTarget` as a file object pointer for rename/link target parent directories when the target name is qualified or rooted. Microsoft documents `FILE_RENAME_INFORMATION` and `FILE_LINK_INFORMATION` as carrying `RootDirectory`, `FileNameLength`, and `FileName`. Microsoft documents `FltSetInformationFile` as the minifilter set-information routine with `Length` as the byte size of the information buffer. |
| Fix | Comment-only source clarification. The disabled old direct check now names SREV-332 and says `ParentOfTarget` is a file-object carrier while `File_RenameOperation` owns target-context parsing. No set-information class predicate, length gate, `RelatedFileObject` fallback, parser call, or return status changed. |
| Acceptance Gate | `docs/plan/check-srev-332.py` validates the draft-07 schema, official references, source routing from set-information classes to `File_RenameOperation`, the `ParentOfTarget` requirement, SREV-019 length gates, `RelatedFileObject` fallback, `File_Generic_MyParseProc` target-directory context, stale bug wording removal, combined ledger entry, and split ledger fragment; `docs/plan/check-srev-332.sh` is the targeted wrapper. Runtime gate: Windows rename/link matrix covering rooted target parent, relative target parent, network-drive related-file-object fallback, inside-box target, outside-box target denial, and SREV-019 long/malformed name regression. |
