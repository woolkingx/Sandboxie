---
kind: srev-ledger-entry
id: SREV-155
title: File Reparse Cache Counted Object Name
status: patched-source-level-after-official-object-name-and-unicode-string-review-needs-windows-runtime-proof
owner: Sandboxie/core/drv/file_xlat.c
spec: docs/plan/srev-155-file-xlat-counted-object-name.md
schema: docs/plan/srev-155-file-xlat-counted-object-name.schema.json
checker: docs/plan/check-srev-155.py
runtime_gate: Windows reparse translation cache and object-name runtime proof
---

### SREV-155: File Reparse Cache Counted Object Name

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official object-name and `UNICODE_STRING` review; needs Windows reparse translation runtime proof |
| Evidence | `Sandboxie/core/drv/file_xlat.c` is the top unnamed reviewable core file after SREV-154. `File_TranslateReparsePoints_3` opens a candidate directory, references the `FILE_OBJECT`, calls `Obj_GetName`, and caches the returned object name as `CACHE_PATH::dst`. Before this SREV, the cache destination length was computed with `wcslen(Name->Name.Buffer)`, treating `OBJECT_NAME_INFORMATION.Name.Buffer` as a C string instead of using the counted `UNICODE_STRING.Length`. |
| Data | `File_TranslateReparsePoints`, `File_TranslateReparsePoints_2`, `File_TranslateReparsePoints_3`, `File_ReparsePointsBusy`, `CACHE_PATH`, `src_len`, `dst_len`, `dst`, `ZwCreateFile`, `FILE_DIRECTORY_FILE`, `FILE_SYNCHRONOUS_IO_NONALERT`, `ObReferenceObjectByHandle`, `Obj_GetName`, `OBJECT_NAME_INFORMATION.Name`, `UNICODE_STRING.Length`, `Name->Name.Buffer`, `NameLength`, and KPATH-002. |
| Schema | `FILE_XLAT_COUNTED_OBJECT_NAME` says `OBJECT_NAME_INFORMATION.Name` is a counted `UNICODE_STRING`, `UNICODE_STRING.Length` is a byte count and does not include a trailing null character when one is present, `File_TranslateReparsePoints_3` derives `CACHE_PATH` destination length from `Name->Name.Length`, the length must be `WCHAR`-aligned before converting bytes to a character count, trailing backslash trimming stays inside that counted extent, and this SREV does not change KPATH-002 `File_ReparsePointsBusy` wait behavior. |
| Topology | Legal flow is `ZwCreateFile` on the directory path, `ObReferenceObjectByHandle(FILE_OBJECT)`, `Obj_GetName` / `ObQueryNameString`, `OBJECT_NAME_INFORMATION.Name.Length` counted extent, trailing-backslash trim within that extent, `CACHE_PATH::dst` allocation/copy, then reparse translation cache insertion under `File_ReparsePointsLock`. |
| Logic Risk | The old code crossed from counted kernel object-name data to a C-string scan before allocating and copying the cache destination. Even though `ObQueryNameString` commonly provides a null-terminated buffer, allocation and copy boundaries should use the `UNICODE_STRING.Length` owner field instead of a terminator search. |
| Official Shape | `docs/plan/srev-155-file-xlat-counted-object-name.md` records Microsoft `ObQueryNameString`, `UNICODE_STRING`, and `RtlInitUnicodeString` references. `docs/plan/srev-155-file-xlat-counted-object-name.schema.json` records the JSON Schema draft-07 local `FILE_XLAT_COUNTED_OBJECT_NAME` contract. |
| Fix | `file_xlat.c` now requires `Name->Name.Buffer` and `Name->Name.Length` alignment, computes `dst_len` as `Name->Name.Length / sizeof(WCHAR)`, and trims trailing backslashes by indexing `Name->Name.Buffer` only within that counted extent. The cache allocation/copy topology, `ZwCreateFile` flags, `Obj_GetName` ownership, pass behavior, and KPATH-002 busy-wait runtime design are otherwise unchanged. |
| Acceptance Gate | `docs/plan/check-srev-155.py` validates the draft-07 schema, official references, counted object-name use, removal of the stale `wcslen(Name->Name.Buffer)` path, preservation of `ZwCreateFile` / `Obj_GetName` / cache-copy topology, unchanged KPATH-002 boundary, and ledger fragment; `docs/plan/check-srev-155.sh` is the matrix wrapper. Runtime/build gate: Windows driver build for `file_xlat.c`; reparse/junction translation smoke proving ordinary object names still cache and rewrite; instrumented object-name cases with counted length and terminator variance; slow/offline reparse path observation for KPATH-002; Driver Verifier and HVCI where supported. |
