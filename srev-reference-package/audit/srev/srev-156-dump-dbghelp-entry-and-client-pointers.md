# SREV-156: Dump DbgHelp Entry And Client Pointers

## Stage Gate

| Field | Content |
|---|---|
| Stage | schema -> boundary -> topology -> logic -> action -> verify |
| Input artifact | `Sandboxie/core/dll/dump.c`, `Sandboxie/install/SbieSettings.ini`, Microsoft DbgHelp / loader / unhandled-exception references |
| Output artifact | Source-level crash-dump entry hardening, draft-07 schema, checker, ledger fragment |
| Owner | `Sandboxie/core/dll/dump.c` owns in-process minidump setup and crash-handler dump creation |
| Acceptance gate | Source proves `MiniDumpWriteDump` is resolved before the handler can call it and in-process exception pointers use `ClientPointers = FALSE` |

## Data

`Dump_Init` runs when `EnableMiniDump` is enabled for an image. It loads
`dbghelp.dll`, resolves `MiniDumpWriteDump`, reads optional `MiniDumpFlags`,
registers `Dump_CrashHandlerExceptionFilter`, and hooks later
`SetUnhandledExceptionFilter` calls so the Sandboxie handler remains installed.

The crash filter creates a dump file under `Dll_BoxFilePath`, fills
`MINIDUMP_EXCEPTION_INFORMATION` from the current exception, and calls
`MiniDumpWriteDump` for `GetCurrentProcess()`.

Before this SREV, two boundaries were wrong:

- `Dump_Init` did not check whether `GetProcAddress(..., "MiniDumpWriteDump")`
  returned `NULL`, but the crash filter later called the function pointer.
- `Dump_CrashHandlerExceptionFilter` set `stMDEI.ClientPointers = TRUE` even
  though the exception pointers are local to the calling process.

## Official Shape

Microsoft documents `GetProcAddress` as returning `NULL` on failure. Code using
run-time dynamic linking must handle missing functions before calling through
the returned pointer.

Microsoft documents `MiniDumpWriteDump` as the DbgHelp function that writes a
user-mode minidump. It also warns that DbgHelp functions are single-threaded and
that calling from inside the crashed process is riskier than using another
process or a dedicated thread. This SREV does not redesign Sandboxie's in-process
dump architecture; it only hardens the source-local entry contract.

Microsoft documents `MINIDUMP_EXCEPTION_INFORMATION.ClientPointers` as selecting
where `ExceptionPointers` memory resides. It says to set `ClientPointers` to
`TRUE` when the memory resides in the target process of a debugger, and to set
it to `FALSE` when the memory resides in the calling program. The same page
states that local memory in the calling process should not use `TRUE`.

Microsoft documents `SetUnhandledExceptionFilter` as replacing the process-wide
top-level exception filter and returning the previous filter. The filter runs in
the faulting thread context.

Official references:

- `https://learn.microsoft.com/en-us/windows/win32/api/libloaderapi/nf-libloaderapi-getprocaddress`
- `https://learn.microsoft.com/en-us/windows/win32/api/minidumpapiset/nf-minidumpapiset-minidumpwritedump`
- `https://learn.microsoft.com/en-us/windows/win32/api/minidumpapiset/ns-minidumpapiset-minidump_exception_information`
- `https://learn.microsoft.com/en-us/windows/win32/api/errhandlingapi/nf-errhandlingapi-setunhandledexceptionfilter`

## Topology

Legal flow:

```text
EnableMiniDump
  -> Dump_Init
  -> LoadLibrary(dbghelp.dll)
  -> GetProcAddress(MiniDumpWriteDump)
  -> if missing: FreeLibrary + clear Dump_DbgHelpMod + no handler install
  -> if present: SetUnhandledExceptionFilter(Dump_CrashHandlerExceptionFilter)
  -> faulting thread exception pointers
  -> local MINIDUMP_EXCEPTION_INFORMATION with ClientPointers = FALSE
  -> MiniDumpWriteDump
```

This SREV does not change dump flags, dump file path, `SetUnhandledExceptionFilter`
blocking policy, stack-overflow x86 shim, or the fact that Sandboxie writes dumps
from inside the crashed process.

## Logic Risk

A crash handler must not add a second crash path before reaching the dump write.
If `dbghelp.dll` loads but `MiniDumpWriteDump` cannot be resolved, installing the
handler leaves the next application crash pointed at a NULL function pointer.

The `ClientPointers` field is also part of the dump schema. Sandboxie passes
exception pointers from the same process and same faulting thread into
`MiniDumpWriteDump(GetCurrentProcess(), ...)`; the local-memory shape is
`ClientPointers = FALSE`, not the remote-debugger target-memory shape.

## Fix

`Dump_Init` now treats a missing `MiniDumpWriteDump` export as initialization
failure: it frees `Dump_DbgHelpMod`, clears the module handle, and returns `0`
before installing the unhandled-exception filter. The crash filter also guards
the call through `__sys_MiniDumpWriteDump`.

`Dump_CrashHandlerExceptionFilter` now sets
`MINIDUMP_EXCEPTION_INFORMATION.ClientPointers` to `FALSE` for local in-process
exception pointers.

## Acceptance Gate

`docs/plan/check-srev-156.py` validates the draft-07 schema, official
references, `GetProcAddress` failure handling, `FreeLibrary` / clear / return
before handler installation, guarded crash-filter call, local
`ClientPointers = FALSE`, unchanged dump file / flags / hook topology, and
ledger fragment.

Runtime/build gate: Windows DLL build for `dump.c`; `EnableMiniDump=y` crash
smoke proving a dump is written; injected `GetProcAddress` failure proving no
handler install and no NULL-call crash; local exception-pointer minidump
inspection; stack-overflow x86 smoke where applicable; concurrent crash
observation remains a DbgHelp architecture risk because DbgHelp is
single-threaded.
