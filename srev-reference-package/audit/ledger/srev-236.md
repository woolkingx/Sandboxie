---
kind: srev-ledger-entry
id: SREV-236
title: Debug Header Topology Contract
status: docs-only-source-topology-reviewed-needs-windows-dll-build-proof
owner: Sandboxie/core/dll/debug.h
additional_owners:
  - Sandboxie/core/dll/debug.c
  - Sandboxie/core/dll/dllmain.c
  - Sandboxie/core/dll/SboxDll.vcxproj
  - docs/plan/ledger/srev-146.md
spec: docs/plan/srev-236-debug-header-topology.md
schema: docs/plan/srev-236-debug-header-topology.schema.json
checker: docs/plan/check-srev-236.py
runtime_gate: Windows SboxDll build continues to compile debug.h and wire debug callers to debug.c; runtime behavior remains covered by existing and future concrete-owner SREV Windows gates.
---

### SREV-236: Debug Header Topology Contract

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | docs-only source topology reviewed; needs Windows DLL build proof |
| Evidence | `Sandboxie/core/dll/debug.h` was the top unnamed reviewable core file after SREV-235. Source readback shows it is the declaration header for the DLL debug helper. It declares the always-compiled `Debug_Wait` entry point and, when `WITH_DEBUG` is defined, the `BREAK_IMAGE_1` local debug macro and `Debug_Init`. Runtime ownership lives in `debug.c`, `dllmain.c`, and `SboxDll.vcxproj`. SREV-146 already owns the concrete debug-format buffer termination risk in `debug.c`. |
| Data | `Debug_Wait`, `Debug_Init`, `WITH_DEBUG`, `BREAK_IMAGE_1`, `WaitForDebuggerAll`, `WaitForDebugger`, `WaitForDebuggerCmdLine`, `WaitForDebuggerSilent`, `IsDebuggerPresent`, `OutputDebugString`, `Sleep`, `__debugbreak`, `DbgPrint`, `DbgTrace`, `debug.c`, `dllmain.c`, and `SboxDll.vcxproj`. |
| Schema | `DEBUG_HEADER_TOPOLOGY_CONTRACT` says `debug.h` is the DLL debug helper declaration header; it may declare `Debug_Wait`, conditionally declare `Debug_Init`, and keep local debug-only break-image macros; it does not own debugger wait policy, config reads, debug hook installation, output formatting, debugger event handling, or `DbgPrint` / `DbgTrace` buffer safety; runtime behavior changes belong to `debug.c`, `dllmain.c`, or `SboxDll.vcxproj`, depending on the transition; and future header changes must prove caller topology and concrete runtime owner before behavior claims. |
| Topology | `dllmain.c -> Debug_Wait -> debug.c config reads -> IsDebuggerPresent / OutputDebugString / Sleep / __debugbreak`; `SboxDll.vcxproj WITH_DEBUG -> debug.h exposes Debug_Init -> dllmain.c conditionally calls Debug_Init -> debug.c optional debug hook scaffolding and disabled break-image block`; `SREV-146 -> debug.c DbgPrint / DbgTrace buffer termination -> Windows WITH_DEBUG DLL build and debug-format runtime proof`. |
| Logic Risk | The high coverage score comes from `debug.h` naming NT/debug/COM-adjacent signals and a currently enabled `WITH_DEBUG` build surface. Patching the header would be the wrong route unless the bug is declaration ownership itself. Behavior reviews must target the executable owner where the boundary is crossed. |
| Official Shape | Microsoft documents `IsDebuggerPresent` as a same-process user-mode debugger query, `OutputDebugStringW` as debugger-output emission, `Sleep` as suspending the current thread for an interval, and `DebugBreak` as causing a breakpoint exception in the current process. Those APIs explain the debug-wait behavior in `debug.c`; they do not make `debug.h` the owner of that behavior. |
| Fix | No source patch. This SREV records `debug.h` as a declaration/topology header and closes it as docs-only coverage. Future behavior patches should target the owner that executes the relevant debugger wait, hook, output, startup, or build transition. |
| Acceptance Gate | `docs/plan/check-srev-236.py` validates the draft-07 schema, header declaration shape, `debug.c` implementation topology, `dllmain.c` caller topology, `SboxDll.vcxproj` build topology, existing SREV-146 owner coverage, split ledger fragment, and absence of runtime owner code in this header; `docs/plan/check-srev-236.sh` is the targeted wrapper. Runtime/build gate: Windows `SboxDll` build continues to compile `debug.h` and wire debug callers to `debug.c`; runtime behavior remains covered by existing and future concrete-owner SREV Windows gates. |
