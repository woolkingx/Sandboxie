# SREV-205: MSCOREE CLR Entry Hook Boundary

## Stage

schema -> boundary -> topology -> logic -> verify

## Evidence

`Sandboxie/core/dll/mscoree.c` was the top unnamed reviewable core file after
SREV-204. It hooks `mscoree.dll!_CorExeMain` so Sandboxie can run delayed
injection initialization for managed executable images whose normal image entry
point may be zero.

Local source review shows no deterministic source patch justified at this
boundary. `MsCorEE_Init` resolves `_CorExeMain`, copies the resolved pointer to
the local hook source variable, and then uses `SBIEDLL_HOOK`; the shared hook
macro returns `FALSE` if hook installation does not return an original function
pointer. `MsCorEE__CorExeMain` then calls `Ldr_LoadInjectDlls` once before
calling the captured original `_CorExeMain`.

## Data

`mscoree.c`, `MsCorEE_Init`, `MsCorEE__CorExeMain`, `DllName_mscoree`,
`Ldr_GetProcAddrNew`, `SBIEDLL_HOOK`, `__sys__CorExeMain`, `_CorExeMain`,
`Ldr_LoadInjectDlls`, `g_bHostInject`, `Dll_OsBuild`, and the local
`ReadImageFileExecOptions` PEB byte workaround.

## Official Shape

Microsoft documents `_CorExeMain` as the function called by the loader in
processes created from managed executable assemblies. It initializes the CLR,
locates the managed entry point in the assembly CLR header, and starts
execution.

Microsoft also documents `_CorValidateImage` as the loader path that detects a
managed module, loads `MsCorEE.dll`, and for executable images causes the
loader to call `_CorExeMain` regardless of the image entry point specified in
the file. That matches the local comment in `ldr_init.c` that some .NET
programs have a zero entrypoint and need this `mscoree.dll` entry hook.

References:

- `https://learn.microsoft.com/en-us/dotnet/framework/unmanaged-api/hosting/corexemain-function`
- `https://learn.microsoft.com/en-us/dotnet/framework/unmanaged-api/hosting/corvalidateimage-function`
- `https://learn.microsoft.com/en-us/dotnet/framework/unmanaged-api/hosting/deprecated-clr-hosting-functions`

## Schema

`MSCOREE_CLR_ENTRY_HOOK_BOUNDARY` says:

- `_CorExeMain` is the managed executable loader entry, not a normal Win32
  process entry point.
- `mscoree.c` owns only the delayed Sandboxie injection edge before delegating
  to the original `_CorExeMain`.
- Hook installation must fail closed when the original `_CorExeMain` cannot be
  resolved or captured.
- `Ldr_LoadInjectDlls` is called at most once from this hook instance before
  delegating to the original CLR entry.
- The private PEB `ReadImageFileExecOptions` byte workaround is recorded as a
  runtime compatibility dependency, not treated as public API shape.
- This SREV intentionally makes no source mutation.

## Topology

```text
managed EXE loader
-> mscoree.dll!_CorExeMain
-> Sandboxie hook MsCorEE__CorExeMain
-> one-time PEB workaround and Ldr_LoadInjectDlls(g_bHostInject)
-> original _CorExeMain
-> CLR initialization and managed entrypoint
```

## Logic Risk

The important risk is not a missing local null check today. The shared
`SBIEDLL_HOOK` macro already makes hook installation fail closed if it cannot
capture an original function. The remaining risk is architectural: the hook
depends on CLR loader behavior and a private PEB byte workaround. That should be
kept visible as a runtime compatibility gate instead of being papered over with
an unproven source patch.

## Fix

No source mutation. This entry records the official CLR loader shape and the
local hook boundary so future review does not mistake `_CorExeMain` for an
ordinary application entry point or patch the private PEB workaround without
runtime evidence.

## Acceptance Gate

`docs/plan/check-srev-205.py` validates the draft-07 schema, official
references, local `_CorExeMain` hook topology, shared fail-closed hook macro,
zero-entrypoint evidence in `ldr_init.c`, split ledger fragment, and absence of
a source patch requirement. Runtime/build gate: Windows DLL build plus managed
EXE smoke proving delayed injection runs once and the original `_CorExeMain`
still starts the CLR.
