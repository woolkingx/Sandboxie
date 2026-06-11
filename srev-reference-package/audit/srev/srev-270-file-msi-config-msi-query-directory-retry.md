# SREV-270: File MSI Config.Msi Query Directory Retry

## Stage Gate

| Field | Value |
|---|---|
| Stage | schema -> topology -> logic -> action -> verify |
| Input artifact | `Sandboxie/core/dll/file.c`, Microsoft `UNICODE_STRING`, `NtQueryAttributesFile`, `NtCreateFile`, and `CreateDirectory` documentation |
| Output artifact | `docs/plan/srev-270-file-msi-config-msi-query-directory-retry.schema.json`, `docs/plan/check-srev-270.py`, `docs/plan/check-srev-270.sh`, ledger fragment, source hardening |
| Owner | `File_NtQueryFullAttributesFile` MSI `Config.Msi` compatibility retry |
| Acceptance gate | targeted source checker, core coverage, and diff checkpoint |

## Evidence

`File_NtQueryFullAttributesFile` retries a failed `Config.Msi` attribute query
for `msiexec.exe`: when `File_NtQueryFullAttributesFileImpl` returns
`STATUS_OBJECT_NAME_NOT_FOUND` for `\??\C:\Config.Msi`, the wrapper creates the
directory and retries the query.

Before this SREV, the branch checked `ObjectAttributes->ObjectName->Length == 34`
and then used `_wcsicmp(ObjectName->Buffer + 6, L"\\Config.Msi")` plus
`CreateDirectory(ObjectName->Buffer, NULL)`. That assumed the `UNICODE_STRING`
buffer was NUL-terminated, but `Length` alone does not prove that.

## Official Shape

Microsoft documents `UNICODE_STRING.Length` as the byte length of `Buffer`,
excluding a trailing NULL character if one exists. `MaximumLength` is the
allocated byte capacity.

Microsoft documents `NtQueryAttributesFile` as receiving `OBJECT_ATTRIBUTES` for
the file object and returning basic file attributes. Sandboxie routes
`NtQueryAttributesFile` through `NtQueryFullAttributesFile` to share policy.

Microsoft documents `CreateDirectory` as taking a path to create and applying a
default security descriptor when security attributes are `NULL`; it creates only
the final directory and returns `ERROR_PATH_NOT_FOUND` when intermediate
directories are missing.

Microsoft documents `NtCreateFile.FILE_DIRECTORY_FILE` with `FILE_OPEN_IF` as
the kernel create/open shape for directory files; this SREV does not switch the
existing Win32 `CreateDirectory` behavior, but records the legal directory
creation semantics.

```text
https://learn.microsoft.com/en-us/windows/win32/api/ntdef/ns-ntdef-_unicode_string
https://learn.microsoft.com/en-us/windows/win32/devnotes/ntqueryattributesfile
https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-createdirectory
https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/nf-ntifs-ntcreatefile
```

## Data

`File_NtQueryFullAttributesFile`, `STATUS_OBJECT_NAME_NOT_FOUND`,
`DLL_IMAGE_MSI_INSTALLER`, `OBJECT_ATTRIBUTES.ObjectName`, `UNICODE_STRING`
`Length` / `MaximumLength` / `Buffer`, `\??\C:\Config.Msi`,
`CreateDirectory`, and the retry call to `File_NtQueryFullAttributesFileImpl`.

## Schema

`FILE_MSI_CONFIG_MSI_QUERY_DIRECTORY_RETRY` says:

- the retry is legal only for `DLL_IMAGE_MSI_INSTALLER` after
  `STATUS_OBJECT_NAME_NOT_FOUND`;
- the path match is the exact 17-WCHAR `\??\X:\Config.Msi` shape, represented
  by `Length == 34`;
- because `CreateDirectory` consumes a NUL-terminated path, `MaximumLength` must
  prove room for the trailing NUL and the NUL must be present;
- the `Config.Msi` suffix comparison must be length-bounded and must not rely
  on `_wcsicmp` walking past `Length`;
- this SREV does not change the MSI image gate, status gate, target path shape,
  default security attributes, or retry count.

## Topology

```text
MSI NtQueryFullAttributesFile
  -> Sandboxie full-attributes implementation
  -> STATUS_OBJECT_NAME_NOT_FOUND for Config.Msi
  -> validate UNICODE_STRING exact path and trailing NUL
  -> CreateDirectory(ObjectName->Buffer, NULL)
  -> retry full-attributes implementation
```

## Logic Risk

Without the `MaximumLength` / trailing-NUL gate, the compatibility branch can
read past the legal `UNICODE_STRING.Length` during suffix comparison or while
passing the buffer to `CreateDirectory`. This is a local user-mode hook path, but
it is still an owner-boundary violation: the branch converts a length-delimited
NT object name into a NUL-terminated Win32 path.

## Fix

The branch now stages `ObjectName`, checks `MaximumLength >= Length +
sizeof(WCHAR)`, verifies `Buffer[Length / sizeof(WCHAR)] == L'\0'`, replaces the
unbounded `_wcsicmp` with `_wcsnicmp(..., 11)`, and passes the already-gated
`ObjectName->Buffer` to `CreateDirectory`. The MSI image gate, exact path length,
directory creation call, and single retry are unchanged.

## Acceptance Gate

`docs/plan/check-srev-270.py` validates the draft-07 schema, official references,
MSI/status/path gates, `UNICODE_STRING` trailing-NUL proof, length-bounded suffix
comparison, `CreateDirectory` call using the gated pointer, single retry, removal
of stale unbounded `_wcsicmp` shape, and the ledger fragment.

Runtime gate: Windows MSI install/repair smoke that probes `\??\C:\Config.Msi`,
creates the directory when missing, retries attributes successfully, and does not
take the retry for non-MSI callers, non-`Config.Msi` paths, or non-NUL-terminated
object names.
