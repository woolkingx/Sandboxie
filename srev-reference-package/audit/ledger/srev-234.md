---
kind: srev-ledger-entry
id: SREV-234
title: Trace Header Topology Contract
status: docs-only-source-topology-reviewed-needs-windows-dll-build-proof
owner: Sandboxie/core/dll/trace.h
additional_owners:
  - Sandboxie/core/dll/trace.c
  - Sandboxie/core/dll/dllmain.c
  - Sandboxie/core/dll/dllhook.c
  - Sandboxie/core/dll/rpcrt.c
  - Sandboxie/core/dll/file_misc.c
  - Sandboxie/core/dll/sbieapi.c
  - Sandboxie/core/dll/callsvc.c
spec: docs/plan/srev-234-trace-header-topology.md
schema: docs/plan/srev-234-trace-header-topology.schema.json
checker: docs/plan/check-srev-234.py
runtime_gate: Windows SboxDll build continues to compile trace.h and wire trace callers to trace.c; trace runtime behavior remains covered by existing and future concrete-owner SREV Windows gates.
---

### SREV-234: Trace Header Topology Contract

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | docs-only source topology reviewed; needs Windows DLL build proof |
| Evidence | `Sandboxie/core/dll/trace.h` was the top unnamed reviewable core file after SREV-233. Source readback shows it is the declaration header for the DLL trace helper. It declares `Trace_Init`, `Trace_Entry`, address-to-module/export helper functions, `BufferToHexW`, and the external `Dll_HookTrace` flag. Runtime ownership lives in `trace.c`, `dllmain.c`, `dllhook.c`, `rpcrt.c`, `file_misc.c`, `sbieapi.c`, and `callsvc.c`. |
| Data | `Trace_Init`, `Trace_Entry`, `Trace_FindModuleByAddress`, `Trace_FindExportByAddress`, `BufferToHexW`, `Dll_HookTrace`, `Dll_SbieTrace`, `Dll_ApiTrace`, `Dll_FileTrace`, `ApiInstrumentation`, `InstrumentationTrace`, `Trace_SbieDrvFunc2Str`, `Trace_SbieSvcFunc2Str`, `Trace_SbieGuiFunc2Str`, `dllmain.c`, `dllhook.c`, `rpcrt.c`, `file_misc.c`, `sbieapi.c`, and `callsvc.c`. |
| Schema | `TRACE_HEADER_TOPOLOGY_CONTRACT` says `trace.h` is the DLL trace helper declaration header; it may declare trace lifecycle helpers, address lookup helpers, formatting helpers, and externally consumed trace flags; it does not own hook installation, `OutputDebugString`/`RtlSetLastWin32Error` interception, private `ProcessInstrumentationCallback` setup, architecture-specific trampoline ABI, monitor log record shape, API/service/GUI id lookup-table completeness, or module/export parsing behavior; runtime behavior changes belong to the concrete owner that executes the transition; and future header changes must prove caller topology and concrete runtime owner before behavior claims. |
| Topology | `dllmain.c -> Trace_Init -> trace.c config reads and optional hooks/instrumentation setup -> trace output via SbieApi_MonitorPut* / monitor APIs`; `dllmain.c -> Trace_Entry -> debug-only entry trace`; `dllhook.c / rpcrt.c / file_misc.c -> Trace_FindModuleByAddress / Trace_FindExportByAddress -> trace.c PEB loader-list or PE export lookup -> diagnostic monitor output`; `trace.c -> Trace_SbieDrvFunc2Str / Trace_SbieSvcFunc2Str / Trace_SbieGuiFunc2Str -> sbieapi.c / callsvc.c local extern consumers`. |
| Logic Risk | The high coverage score comes from `trace.h` naming trace, hook, COM/RPC diagnostic, and NT-facing helper surfaces. Patching the header would be the wrong route unless the bug is declaration ownership itself. Behavior reviews must target the executable owner where the boundary is crossed. |
| Official Shape | No new Windows/API runtime behavior is defined by this header. The official API and ABI references for the underlying behavior remain in SREV-093, SREV-095, SREV-177, SREV-028, and SREV-220. This SREV is a local declaration/topology classification. |
| Fix | No source patch. This SREV records `trace.h` as a declaration/topology header and closes it as docs-only coverage. Future behavior patches should target the owner that executes the relevant hook, instrumentation, monitor, module lookup, export lookup, or id-to-string transition. |
| Acceptance Gate | `docs/plan/check-srev-234.py` validates the draft-07 schema, header declaration shape, trace implementation topology in `trace.c`, caller topology in `dllmain.c`, `dllhook.c`, `rpcrt.c`, `file_misc.c`, `sbieapi.c`, and `callsvc.c`, existing trace/monitor SREV owner coverage, split ledger fragment, and absence of runtime owner claims for this header; `docs/plan/check-srev-234.sh` is the targeted wrapper. Runtime/build gate: Windows `SboxDll` build continues to compile `trace.h` and wire trace callers to `trace.c`; trace runtime behavior remains covered by the existing and future concrete-owner SREV Windows gates. |
