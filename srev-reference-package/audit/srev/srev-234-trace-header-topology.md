# SREV-234: Trace Header Topology Contract

## Stage

data -> schema -> boundary -> topology -> logic -> verify

## Evidence

After SREV-233, `Sandboxie/core/dll/trace.h` was the top unnamed reviewable core
file. Source readback shows it is the declaration header for the DLL trace
helper. It declares `Trace_Init`, `Trace_Entry`, address-to-module/export helper
functions, `BufferToHexW`, and the external `Dll_HookTrace` flag.

The runtime owners are elsewhere:

- `Sandboxie/core/dll/trace.c` owns trace initialization, debug/error trace
  hooks, private process instrumentation callback setup, module/export lookup,
  buffer-to-hex formatting, API-name lookup tables, and monitor trace emission.
- `Sandboxie/core/dll/dllmain.c` owns DLL initialization/entry sequencing and
  calls `Trace_Init` / `Trace_Entry`.
- `Sandboxie/core/dll/dllhook.c` owns API trace detour emission and hook trace
  list state.
- `Sandboxie/core/dll/rpcrt.c` and `file_misc.c` consume address-to-module or
  address-to-export helpers for trace/diagnostic output.
- `Sandboxie/core/dll/sbieapi.c` and `callsvc.c` declare local externs for
  `Trace_SbieDrvFunc2Str`, `Trace_SbieSvcFunc2Str`, and
  `Trace_SbieGuiFunc2Str`; those lookup-table functions are implemented in
  `trace.c` but are not part of `trace.h`.

Existing SREV coverage already owns the behavior-heavy trace risks: SREV-093
classifies the private process instrumentation API boundary in `trace.c`;
SREV-095 classifies the native ARM64 API trace trampoline ABI; SREV-177 fixes
the ARM64EC API trace argument preservation path; SREV-028 and SREV-220 cover
driver monitor readback shape used by trace output.

## Data

`Trace_Init`, `Trace_Entry`, `Trace_FindModuleByAddress`,
`Trace_FindExportByAddress`, `BufferToHexW`, `Dll_HookTrace`, `Dll_SbieTrace`,
`Dll_ApiTrace`, `Dll_FileTrace`, `ApiInstrumentation`, `InstrumentationTrace`,
`Trace_SbieDrvFunc2Str`, `Trace_SbieSvcFunc2Str`, `Trace_SbieGuiFunc2Str`,
`dllmain.c`, `dllhook.c`, `rpcrt.c`, `file_misc.c`, `sbieapi.c`, and
`callsvc.c`.

## Schema

`TRACE_HEADER_TOPOLOGY_CONTRACT` says:

- `trace.h` is the DLL trace helper declaration header.
- The header may declare trace lifecycle helpers, address lookup helpers,
  formatting helpers, and externally consumed trace flags.
- The header must not be treated as the owner of hook installation,
  `OutputDebugString`/`RtlSetLastWin32Error` interception, private
  `ProcessInstrumentationCallback` setup, architecture-specific trampoline ABI,
  monitor log record shape, API/service/GUI id lookup-table completeness, or
  module/export parsing behavior.
- Runtime behavior changes belong to `trace.c`, `dllmain.c`, `dllhook.c`,
  `rpcrt.c`, `file_misc.c`, `sbieapi.c`, or `callsvc.c`, depending on the
  transition.
- Future changes to this header must prove the caller topology and concrete
  runtime owner before making behavior claims.

## Topology

```text
dllmain.c
-> Trace_Init
-> trace.c config reads and optional hooks/instrumentation setup
-> trace output via SbieApi_MonitorPut* / monitor APIs

dllmain.c
-> Trace_Entry
-> debug-only entry trace

dllhook.c / rpcrt.c / file_misc.c
-> Trace_FindModuleByAddress / Trace_FindExportByAddress
-> trace.c PEB loader-list or PE export lookup
-> diagnostic monitor output

trace.c
-> Trace_SbieDrvFunc2Str / Trace_SbieSvcFunc2Str / Trace_SbieGuiFunc2Str
-> sbieapi.c / callsvc.c local extern consumers
```

The header is the declaration node. It is not the owner of private NT process
information, monitor wire shape, hook-detour ABI, or export-table parsing.

## Logic Risk

The high coverage score comes from `trace.h` naming trace, hook, COM/RPC
diagnostic, and NT-facing helper surfaces. Patching the header would be the
wrong route unless the bug is declaration ownership itself. Behavior reviews
must target the executable owner where the boundary is crossed.

## Official Shape

No new Windows/API runtime behavior is defined by this header. The official API
and ABI references for the underlying behavior remain in SREV-093, SREV-095,
SREV-177, SREV-028, and SREV-220. This SREV is a local declaration/topology
classification.

## Fix

No source patch. This SREV records `trace.h` as a declaration/topology header
and closes it as docs-only coverage. Future behavior patches should target the
owner that executes the relevant hook, instrumentation, monitor, module lookup,
export lookup, or id-to-string transition.

## Acceptance Gate

`docs/plan/check-srev-234.py` validates the draft-07 schema, header declaration
shape, trace implementation topology in `trace.c`, caller topology in
`dllmain.c`, `dllhook.c`, `rpcrt.c`, `file_misc.c`, `sbieapi.c`, and
`callsvc.c`, existing trace/monitor SREV owner coverage, split ledger fragment,
and absence of runtime owner claims for this header.

Runtime/build gate: Windows `SboxDll` build continues to compile `trace.h` and
wire trace callers to `trace.c`; trace runtime behavior remains covered by the
existing and future concrete-owner SREV Windows gates.
