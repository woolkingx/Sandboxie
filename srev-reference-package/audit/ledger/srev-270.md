---
kind: srev-ledger-entry
id: SREV-270
title: File MSI Config.Msi Query Directory Retry
status: patched-source-level-after-official-unicode-string-and-directory-create-review-needs-windows-runtime
owner: Sandboxie/core/dll/file.c
spec: docs/plan/srev-270-file-msi-config-msi-query-directory-retry.md
schema: docs/plan/srev-270-file-msi-config-msi-query-directory-retry.schema.json
checker: docs/plan/check-srev-270.py
runtime_gate: Windows MSI install/repair Config.Msi directory-create retry plus non-MSI/non-Config.Msi/non-NUL negative proof
---

### SREV-270: File MSI Config.Msi Query Directory Retry

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official `UNICODE_STRING` and directory-create review; needs Windows MSI runtime proof |
| Evidence | `File_NtQueryFullAttributesFile` retries a failed `Config.Msi` attribute query for `msiexec.exe`: when `File_NtQueryFullAttributesFileImpl` returns `STATUS_OBJECT_NAME_NOT_FOUND` for `\??\C:\Config.Msi`, the wrapper creates the directory and retries the query. Before this SREV, the branch checked `ObjectName->Length == 34` and then used `_wcsicmp(ObjectName->Buffer + 6, L"\\Config.Msi")` plus `CreateDirectory(ObjectName->Buffer, NULL)`, assuming the `UNICODE_STRING` buffer was NUL-terminated. |
| Data | `File_NtQueryFullAttributesFile`, `STATUS_OBJECT_NAME_NOT_FOUND`, `DLL_IMAGE_MSI_INSTALLER`, `OBJECT_ATTRIBUTES.ObjectName`, `UNICODE_STRING` `Length` / `MaximumLength` / `Buffer`, `\??\C:\Config.Msi`, `CreateDirectory`, and the retry call to `File_NtQueryFullAttributesFileImpl`. |
| Schema | `FILE_MSI_CONFIG_MSI_QUERY_DIRECTORY_RETRY` says the retry is legal only for `DLL_IMAGE_MSI_INSTALLER` after `STATUS_OBJECT_NAME_NOT_FOUND`; the path match is the exact 17-WCHAR `\??\X:\Config.Msi` shape represented by `Length == 34`; because `CreateDirectory` consumes a NUL-terminated path, `MaximumLength` must prove room for the trailing NUL and the NUL must be present; the suffix comparison must be length-bounded and must not rely on `_wcsicmp` walking past `Length`; this SREV does not change the MSI image gate, status gate, target path shape, default security attributes, or retry count. |
| Topology | `MSI NtQueryFullAttributesFile -> Sandboxie full-attributes implementation -> STATUS_OBJECT_NAME_NOT_FOUND for Config.Msi -> validate UNICODE_STRING exact path and trailing NUL -> CreateDirectory(ObjectName->Buffer, NULL) -> retry full-attributes implementation`. |
| Logic Risk | Without the `MaximumLength` / trailing-NUL gate, the compatibility branch can read past the legal `UNICODE_STRING.Length` during suffix comparison or while passing the buffer to `CreateDirectory`. This is a local user-mode hook path, but it is still an owner-boundary violation: the branch converts a length-delimited NT object name into a NUL-terminated Win32 path. |
| Official Shape | Microsoft documents `UNICODE_STRING.Length` as byte length excluding a trailing NULL if one exists; `NtQueryAttributesFile` receives `OBJECT_ATTRIBUTES` and returns file attributes; `CreateDirectory` consumes a path string and creates only the final directory; `NtCreateFile.FILE_DIRECTORY_FILE` with `FILE_OPEN_IF` records the kernel directory create/open semantics. |
| Fix | The branch now stages `ObjectName`, checks `MaximumLength >= Length + sizeof(WCHAR)`, verifies `Buffer[Length / sizeof(WCHAR)] == L'\0'`, replaces the unbounded `_wcsicmp` with `_wcsnicmp(..., 11)`, and passes the already-gated `ObjectName->Buffer` to `CreateDirectory`. The MSI image gate, exact path length, directory creation call, and single retry are unchanged. |
| Acceptance Gate | `docs/plan/check-srev-270.py` validates the draft-07 schema, official references, MSI/status/path gates, `UNICODE_STRING` trailing-NUL proof, length-bounded suffix comparison, `CreateDirectory` call using the gated pointer, single retry, removal of stale unbounded `_wcsicmp` shape, and the ledger fragment; `docs/plan/check-srev-270.sh` is the targeted wrapper. Runtime gate: Windows MSI install/repair smoke that probes `\??\C:\Config.Msi`, creates the directory when missing, retries attributes successfully, and does not take the retry for non-MSI callers, non-`Config.Msi` paths, or non-NUL-terminated object names. |
