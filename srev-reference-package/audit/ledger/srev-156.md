---
kind: srev-ledger-entry
id: SREV-156
title: Dump DbgHelp Entry And Client Pointers
status: patched-source-level-after-official-dbghelp-loader-and-exception-pointer-review-needs-windows-runtime-proof
owner: Sandboxie/core/dll/dump.c
spec: docs/plan/srev-156-dump-dbghelp-entry-and-client-pointers.md
schema: docs/plan/srev-156-dump-dbghelp-entry-and-client-pointers.schema.json
checker: docs/plan/check-srev-156.py
runtime_gate: Windows minidump creation and DbgHelp failure runtime proof
---

### SREV-156: Dump DbgHelp Entry And Client Pointers

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official DbgHelp loader / minidump / exception-pointer review; needs Windows minidump runtime proof |
| Evidence | `Sandboxie/core/dll/dump.c` is the top unnamed reviewable core file after SREV-155. `Dump_Init` loads `dbghelp.dll`, resolves `MiniDumpWriteDump`, reads `MiniDumpFlags`, installs `Dump_CrashHandlerExceptionFilter`, and hooks later `SetUnhandledExceptionFilter` calls. Before this SREV, `Dump_Init` did not check whether `GetProcAddress(..., "MiniDumpWriteDump")` returned `NULL`, but the crash filter later called through `__sys_MiniDumpWriteDump`. The crash filter also set `MINIDUMP_EXCEPTION_INFORMATION.ClientPointers = TRUE` while dumping `GetCurrentProcess()` with exception pointers from the same calling process. |
| Data | `Dump_Init`, `Dump_CrashHandlerExceptionFilter`, `Dump_DbgHelpMod`, `__sys_MiniDumpWriteDump`, `LoadLibrary(dbghelp.dll)`, `GetProcAddress`, `FreeLibrary`, `SetUnhandledExceptionFilter`, `SBIEDLL_HOOK(Dump_, SetUnhandledExceptionFilter)`, `MINIDUMP_EXCEPTION_INFORMATION`, `ClientPointers`, `GetCurrentProcess`, `GetCurrentProcessId`, `Dump_Flags`, `MiniDumpFlags`, `EnableMiniDump`, and `Dll_BoxFilePath`. |
| Schema | `DUMP_DBGHELP_ENTRY_AND_CLIENT_POINTERS` says `GetProcAddress` returns `NULL` on failure and `MiniDumpWriteDump` must not be called through a null function pointer; `Dump_Init` must not install the crash filter unless `MiniDumpWriteDump` is resolved; failed resolution frees `Dump_DbgHelpMod`, clears the module handle, and returns `0`; the crash filter guards the function-pointer call; `ClientPointers` is `FALSE` for local exception pointers in the calling process; this SREV does not change `MiniDumpFlags`, dump file path, `SetUnhandledExceptionFilter` blocking policy, or in-process dump architecture. |
| Topology | Legal flow is `EnableMiniDump`, `Dump_Init`, `LoadLibrary(dbghelp.dll)`, `GetProcAddress(MiniDumpWriteDump)`, fail -> `FreeLibrary` / clear / no handler install, success -> read `MiniDumpFlags`, install `Dump_CrashHandlerExceptionFilter`, faulting-thread exception pointers, local `MINIDUMP_EXCEPTION_INFORMATION` with `ClientPointers = FALSE`, and guarded `MiniDumpWriteDump`. |
| Logic Risk | A crash handler must not add a second crash path before the dump write. Loading `dbghelp.dll` successfully does not prove `MiniDumpWriteDump` exists; `GetProcAddress` failure is a legal loader outcome. Also, `ClientPointers` is part of the DbgHelp exception-pointer schema: Sandboxie passes local pointers from the same process, not remote debugger pointers. |
| Official Shape | `docs/plan/srev-156-dump-dbghelp-entry-and-client-pointers.md` records Microsoft `GetProcAddress`, `MiniDumpWriteDump`, `MINIDUMP_EXCEPTION_INFORMATION`, and `SetUnhandledExceptionFilter` references. `docs/plan/srev-156-dump-dbghelp-entry-and-client-pointers.schema.json` records the JSON Schema draft-07 local `DUMP_DBGHELP_ENTRY_AND_CLIENT_POINTERS` contract. |
| Fix | `Dump_Init` now treats a missing `MiniDumpWriteDump` export as initialization failure: it frees `Dump_DbgHelpMod`, clears the module handle, and returns `0` before installing the unhandled-exception filter. The crash filter also checks `__sys_MiniDumpWriteDump` before calling it. `Dump_CrashHandlerExceptionFilter` now sets `ClientPointers = FALSE` for local in-process exception pointers. |
| Acceptance Gate | `docs/plan/check-srev-156.py` validates the draft-07 schema, official references, `GetProcAddress` failure handling, `FreeLibrary` / clear / return before handler installation, guarded crash-filter call, local `ClientPointers = FALSE`, unchanged `MiniDumpFlags` / dump file / hook topology, and ledger fragment; `docs/plan/check-srev-156.sh` is the matrix wrapper. Runtime/build gate: Windows DLL build for `dump.c`; `EnableMiniDump=y` crash smoke proving a dump is written; injected `GetProcAddress` failure proving no handler install and no NULL-call crash; local exception-pointer minidump inspection; stack-overflow x86 smoke where applicable; concurrent crash observation remains a DbgHelp architecture risk because DbgHelp is single-threaded. |
