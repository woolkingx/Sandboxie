# SREV-285: MSO Recovery Module Signal Owner

| Field | Content |
|---|---|
| Stage | schema -> boundary -> verify |
| Input artifact | `Sandboxie/core/dll/ldr.c`, `Sandboxie/core/dll/file_recovery.c`, SREV-072, and Microsoft dynamic-link library documentation |
| Output artifact | Source comment owner, draft-07 schema, checker, and ledger fragment |
| Owner | `mso.dll` module-presence signal for the Office recovery filter |
| Acceptance gate | Targeted checker validates official reference, loader callback registration, `File_MsoDllLoaded` publication, `File_IsRecoverable` Office filter use, SREV-072 adjacency, stale source wording removal, and ledger fragment |

## Data

`ldr.c` registers `File_MsoDll` as the module callback for `mso.dll`.
`File_MsoDll` sets one process-local flag:

```text
File_MsoDllLoaded = TRUE
```

`File_IsRecoverable` uses that flag to apply an Office-specific recovery filter:

```text
if (File_MsoDllLoaded)
  ignore names beginning with ~$
  ignore names without an extension
```

SREV-072 already owns the recoverable-path redirector normalization and MUP
buffer allocation gate. SREV-285 owns only the module-presence signal and its
connection to the Office temp-file recovery filter.

## Official Shape

Microsoft documents DLL functions including `LoadLibrary`, which maps an
executable module into the address space of the calling process, and
`GetModuleHandle`, which retrieves a module handle for a loaded module. That is
the official shape needed here: once a DLL is loaded in the process, local code
may observe module presence and use that as process-local state.

Official references:

- `https://learn.microsoft.com/en-us/windows/win32/dlls/dynamic-link-library-functions`

## Schema

Local schema:

```text
docs/plan/srev-285-mso-recovery-module-signal-owner.schema.json
```

Contract id:

```text
MSO_RECOVERY_MODULE_SIGNAL_OWNER
```

## Boundary

```text
loader module table
  -> mso.dll callback
  -> File_MsoDllLoaded process-local flag
  -> File_IsRecoverable Office temp-file filter
```

The flag is a module-presence signal, not a path owner and not a recovery-list
owner. Recovery folder matching, ignore-list matching, and redirector
normalization remain owned by `File_IsRecoverable` and SREV-072.

## Topology

```text
mso.dll loaded
  -> Ldr module callback table
  -> File_MsoDll
  -> File_MsoDllLoaded = TRUE

File_IsRecoverable
  -> RecoverFolder prefix match
  -> if File_MsoDllLoaded: Office temp-file filter
  -> AutoRecoverIgnore checks
```

## Logic Risk

The old comments described the `mso.dll` callback as a generic hack. That hides
the actual data shape: a module-presence bit that gates Office-specific recovery
classification. Future edits could remove it as unused callback noise or move
the Office filter into generic recovery behavior without proving compatibility.

## Fix

Comment-only source clarification. The loader table and callback now name
SREV-285 and describe `mso.dll` as the module-presence signal for the Office
recovery filter. No behavior changed.

## Acceptance Gate

`docs/plan/check-srev-285.py` validates the draft-07 schema, official reference,
loader callback registration, `File_MsoDllLoaded` flag, Office filter use inside
`File_IsRecoverable`, SREV-072 adjacency, stale source wording removal, and
ledger fragment.

Runtime gate: Windows Office recovery matrix covering mso-loaded and mso-not
loaded processes, recoverable Office documents, `~$` temporary names,
extensionless temporary names, configured `RecoverFolder`, configured
`AutoRecoverIgnore`, and SREV-072 network redirector normalization.
