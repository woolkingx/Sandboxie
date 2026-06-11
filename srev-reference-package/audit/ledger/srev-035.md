---
kind: srev-ledger-entry
id: SREV-035
title: File API Rename Counted String
status: patched-source-level-after-official-unicode-string-probeforread-zwsetinformation
owner: "Sandboxie/core/drv/file.c:1944-1971"
spec: docs/plan/srev-035-file-api-rename-wire.md
schema: docs/plan/srev-035-file-api-rename-wire.schema.json
checker: docs/plan/check-srev-035.py
runtime_gate: "normal rename plus odd-length, embedded-NUL, embedded-backslash, and stale `MaximumLength` malformed inputs fail before authorization/rename side effects"
---
### SREV-035: File API Rename Counted String

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official UNICODE_STRING/ProbeForRead/ZwSetInformationFile/FILE_RENAME_INFORMATION shape analysis; needs Windows rename malformed-input proof |
| Evidence | `Sandboxie/core/drv/file.c:1944-1971` read user `UNICODE_STRING64.Length` with `& ~1`, copied counted bytes into `path`, then used `wcslen(path)` and `wcschr(&name[1], L'\\')` over the copied buffer. The malformed backslash branch returned `STATUS_INVALID_PARAMETER` after `path` allocation without freeing `path`. |
| Data | `API_RENAME_FILE_ARGS` carries a file handle, counted `target_dir`, counted `target_name`, and replace flag from the DLL API into the driver rename path. |
| Schema | `UNICODE_STRING64.Length` is bytes, must be WCHAR-aligned, nonzero, within the local 32000-byte cap, and `<= MaximumLength`. Copied counted strings must not contain embedded NUL before C-string path APIs are used. `target_name` is passed as a simple relative `FILE_RENAME_INFORMATION` name under `RootDirectory`, so it must not contain `\\`. |
| Topology | DLL `SbieApi_RenameFile` builds counted `UNICODE_STRING64` values; driver `File_Api_Rename` probes user buffers, copies them into kernel pool, authorizes the target path, opens the target directory, and calls `ZwSetInformationFile(FileRenameInformation)`. |
| Logic Risk | Odd byte lengths can silently truncate user input. Embedded NUL can make the path authorization string differ from the probed byte range. A malformed target name can leak the allocated kernel path buffer. |
| Official Shape | `docs/plan/srev-035-file-api-rename-wire.md` records Microsoft `UNICODE_STRING`, `ProbeForRead`, `ZwSetInformationFile`, and `FILE_RENAME_INFORMATION` references. `docs/plan/srev-035-file-api-rename-wire.schema.json` records the small local driver API schema. |
| Fix | `File_Api_Rename` now rejects odd byte lengths, validates `Length <= MaximumLength`, scans counted WCHAR segments with `File_Api_RenameContainsWChar`, derives `name` from the counted directory length instead of `wcslen(path)`, rejects backslashes in `target_name` through a counted scan, and frees `path` before malformed-name returns. |
| Acceptance Gate | `docs/plan/check-srev-035.py` validates the schema, official reference list, source counted-string guards, and cleanup branch; `docs/plan/check-srev-035.sh` is the matrix wrapper. Windows gate: normal rename plus odd-length, embedded-NUL, embedded-backslash, and stale `MaximumLength` malformed inputs fail before authorization/rename side effects. |
