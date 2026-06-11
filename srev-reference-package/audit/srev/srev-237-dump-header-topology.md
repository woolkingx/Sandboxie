# SREV-237: Dump Header Topology Contract

## Stage

data -> schema -> boundary -> topology -> logic -> verify

## Evidence

After SREV-236, `Sandboxie/core/dll/dump.h` was the top unnamed reviewable core
file. Source readback shows it is the declaration header for the DLL minidump
helper. It declares only `Dump_Init`.

The runtime owners are elsewhere:

- `Sandboxie/core/dll/dump.c` owns in-process minidump initialization, DbgHelp
  loading, `MiniDumpWriteDump` resolution, crash-handler installation, dump-file
  creation, and `SetUnhandledExceptionFilter` blocking.
- `Sandboxie/core/dll/dllmain.c` owns DLL startup sequencing. It calls
  `Dump_Init` only when `EnableMiniDump` is enabled for the image.
- `Sandboxie/core/dll/SboxDll.vcxproj` owns the project build-surface fact that
  `dump.c` and `dump.h` are included in `SboxDll`.
- SREV-156 already owns the concrete DbgHelp entry and client-pointer risks in
  `dump.c`.

## Data

`Dump_Init`, `EnableMiniDump`, `MiniDumpFlags`, `Dump_CrashHandlerExceptionFilter`,
`Dump_DbgHelpMod`, `MiniDumpWriteDump`, `MINIDUMP_EXCEPTION_INFORMATION`,
`SetUnhandledExceptionFilter`, `dump.c`, `dllmain.c`, and `SboxDll.vcxproj`.

## Schema

`DUMP_HEADER_TOPOLOGY_CONTRACT` says:

- `dump.h` is the DLL minidump helper declaration header.
- The header may declare `Dump_Init`.
- The header does not own DbgHelp loading, `MiniDumpWriteDump` function-pointer
  resolution, minidump flag parsing, crash-handler installation, dump-file path
  construction, exception-pointer shape, or unhandled-exception-filter policy.
- Runtime behavior changes belong to `dump.c`, `dllmain.c`, `SboxDll.vcxproj`,
  or the settings surface, depending on the transition.
- Future changes to this header must prove the caller topology and concrete
  runtime owner before behavior claims.

## Topology

```text
dllmain.c
-> Config_GetSettingsForImageName_bool(EnableMiniDump)
-> Dump_Init
-> dump.c LoadLibrary(dbghelp.dll)
-> GetProcAddress(MiniDumpWriteDump)
-> SetUnhandledExceptionFilter(Dump_CrashHandlerExceptionFilter)
-> faulting thread exception pointers
-> MiniDumpWriteDump

SREV-156
-> dump.c DbgHelp loader contract and local exception-pointer shape
-> Windows minidump runtime proof remains required
```

The header is the declaration node. It is not the owner of DbgHelp ABI,
Sandboxie crash handling, minidump output policy, or exception-pointer memory
shape.

## Logic Risk

The high coverage score comes from `dump.h` naming a minidump helper whose
implementation crosses loader, exception, DbgHelp, file, and settings
boundaries. Patching the header would be the wrong route unless the bug is
declaration ownership itself. Behavior reviews must target the executable owner
where the boundary is crossed.

## Official Shape

No new Windows/API runtime behavior is defined by this header. The official API
references for the underlying behavior remain in SREV-156: `GetProcAddress`,
`MiniDumpWriteDump`, `MINIDUMP_EXCEPTION_INFORMATION`, and
`SetUnhandledExceptionFilter`. This SREV is a local declaration/topology
classification.

## Fix

No source patch. This SREV records `dump.h` as a declaration/topology header and
closes it as docs-only coverage. Future behavior patches should target the owner
that executes the relevant DbgHelp, exception-filter, dump-file, startup, or
settings transition.

## Acceptance Gate

`docs/plan/check-srev-237.py` validates the draft-07 schema, header declaration
shape, `dump.c` implementation topology, `dllmain.c` caller topology,
`SboxDll.vcxproj` build topology, existing SREV-156 owner coverage, split ledger
fragment, and absence of runtime owner code in this header.

Runtime/build gate: Windows `SboxDll` build continues to compile `dump.h` and
wire the `Dump_Init` caller to `dump.c`; runtime behavior remains covered by
existing and future concrete-owner SREV Windows gates.
