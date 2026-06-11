---
kind: srev-ledger-entry
id: SREV-099
title: FLT Copied ABI Comment Contract
status: source-level-classified-after-official-filter-manager-flt-parameters-fltgetfilen
owner: Sandboxie/core/drv/my_fltkernel.h
spec: docs/plan/srev-099-flt-copied-abi-comment-contract.md
schema: docs/plan/srev-099-flt-copied-abi-comment-contract.schema.json
checker: docs/plan/check-srev-099.py
runtime_gate: "Windows/WDK matrix with XP-compatible build settings, Vista+ minifilter load, rename/link callbacks, normalized-name queries, and Driver Verifier observation for copied `FLT_PARAMETERS` layout compatibility"
---
### SREV-099: FLT Copied ABI Comment Contract

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | source-level classified after official Filter Manager `FLT_PARAMETERS`, `FltGetFileNameInformation`, `FLT_FILE_NAME_OPTIONS`, and preoperation callback buffer-access shape; comment-only source clarification, no behavior change |
| Evidence | `Sandboxie/core/drv/my_fltkernel.h` is a local copied/subset Filter Manager header kept because the DDK `fltKernel.h` does not compile when `_WIN32_WINNT < NTDDI_VISTA`, which would prevent XP-compatible driver builds. The flagged comments at `FileSystemControl`, `DeviceIoControl`, and `FLT_FILE_NAME_OPTIONS` used "broken" wording for ordinary ABI partitioning. Microsoft documents `FLT_PARAMETERS` as the minifilter request-specific parameter union, with method-specific `FileSystemControl` and `DeviceIoControl` arms. Microsoft documents `FLT_FILE_NAME_OPTIONS` as a `ULONG` partition for file-name format, query method, and flags. |
| Data | Local copied `my_fltkernel.h`, `FLT_PARAMETERS`, `FileSystemControl.Common/Neither/Buffered/Direct`, `DeviceIoControl.Common/Neither/Buffered/Direct/FastIo`, `FLT_FILE_NAME_OPTIONS`, format mask `0x000000ff`, query-method mask `0x0000ff00`, flag mask `0xff000000`, `FltGetFileNameInformation`, `file_flt.c` `Iopb->Parameters`, and `process.c` `FltGetFileNameInformationUnsafe`. |
| Schema | `FLT_COPIED_ABI_COMMENT_CONTRACT` says `my_fltkernel.h` is a local copied `fltKernel.h` subset kept for `_WIN32_WINNT` below Vista / XP driver build compatibility; this SREV does not change the copied FLT ABI layout or numeric constants; `FLT_PARAMETERS` contains method-specific `FileSystemControl` and `DeviceIoControl` union arms; `FLT_FILE_NAME_OPTIONS` is a `ULONG` partitioned into name format bits, query method bits, unused bits, and flags; `FLT_FILE_NAME_NORMALIZED` and `FLT_FILE_NAME_QUERY_DEFAULT` remain the local normalized-name query contract; comment wording must not describe official partitioned ABI fields as broken. |
| Topology | WDK Filter Manager ABI defines the legal shape. Sandboxie's local copied header mirrors the subset needed for legacy builds. `file_flt.c` consumes that shape through `CallbackData->Iopb`, `Iopb->Parameters`, and `FltGetFileNameInformation(... FLT_FILE_NAME_NORMALIZED \| FLT_FILE_NAME_QUERY_DEFAULT ...)`; `process.c` also uses `FltGetFileNameInformationUnsafe` with the same normalized/default option pair. |
| Logic Risk | The risk was review drift, not a proved runtime defect. The old wording could make a reviewer treat legal ABI partitioning as broken implementation and then mutate copied WDK structure layout. That would cross the wrong owner boundary. Official API shape says the correct source-level move is only to clarify the comments while preserving ABI layout and numeric constants. |
| Official Shape | `docs/plan/srev-099-flt-copied-abi-comment-contract.md` records Microsoft `FLT_PARAMETERS`, `FltGetFileNameInformation`, `FLT_FILE_NAME_OPTIONS`, and preoperation callback buffer-access references. `docs/plan/srev-099-flt-copied-abi-comment-contract.schema.json` records the JSON Schema draft-07 local `FLT_COPIED_ABI_COMMENT_CONTRACT` contract. |
| Fix | Comment-only source clarification: `broken out into` was replaced with `split into` for FSCTL/IOCTL method-specific union arms, and `broken down into` was replaced with `partitioned into` for `FLT_FILE_NAME_OPTIONS` bit sections. No ABI layout, numeric constant, callback registration, or runtime behavior changed. |
| Acceptance Gate | `docs/plan/check-srev-099.py` validates the draft-07 schema, official references, the copied-header XP compatibility reason, `FLT_PARAMETERS` union arms, `FLT_FILE_NAME_OPTIONS` masks and values, stale `broken out into` / `broken down into` removal, local Filter Manager consumers in `file_flt.c` and `process.c`, and ledger entry; `docs/plan/check-srev-099.sh` is the matrix wrapper. Runtime gate: Windows/WDK matrix with XP-compatible build settings, Vista+ minifilter load, rename/link callbacks, normalized-name queries, and Driver Verifier observation for copied `FLT_PARAMETERS` layout compatibility. |
