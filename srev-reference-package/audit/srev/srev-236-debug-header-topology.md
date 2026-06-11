# SREV-236: Debug Header Topology Contract

## Stage

data -> schema -> boundary -> topology -> logic -> verify

## Evidence

After SREV-235, `Sandboxie/core/dll/debug.h` was the top unnamed reviewable core
file. Source readback shows it is the declaration header for the DLL debug
helper. It declares the always-compiled `Debug_Wait` entry point and, when
`WITH_DEBUG` is defined, the `BREAK_IMAGE_1` local debug macro and `Debug_Init`.

The runtime owners are elsewhere:

- `Sandboxie/core/dll/debug.c` owns `Debug_Wait`, `Debug_Init`, debug hook
  scaffolding, debugger wait loops, debug output helpers, and the disabled
  image-name breakpoint block that consumes `BREAK_IMAGE_1`.
- `Sandboxie/core/dll/dllmain.c` owns DLL startup sequencing. It calls
  `Debug_Wait` after process identity is known and calls `Debug_Init` only
  under `WITH_DEBUG`.
- `Sandboxie/core/dll/SboxDll.vcxproj` owns the build-surface fact that
  `WITH_DEBUG` is currently part of the `SboxDll` compile definitions and that
  `debug.c` / `debug.h` are included in the project.
- SREV-146 already owns the concrete debug-format buffer termination risk in
  `debug.c`.

## Data

`Debug_Wait`, `Debug_Init`, `WITH_DEBUG`, `BREAK_IMAGE_1`,
`WaitForDebuggerAll`, `WaitForDebugger`, `WaitForDebuggerCmdLine`,
`WaitForDebuggerSilent`, `IsDebuggerPresent`, `OutputDebugString`, `Sleep`,
`__debugbreak`, `DbgPrint`, `DbgTrace`, `debug.c`, `dllmain.c`, and
`SboxDll.vcxproj`.

## Schema

`DEBUG_HEADER_TOPOLOGY_CONTRACT` says:

- `debug.h` is the DLL debug helper declaration header.
- The header may declare `Debug_Wait`, conditionally declare `Debug_Init`, and
  keep local debug-only break-image macros.
- The header does not own debugger wait policy, config reads, debug hook
  installation, output formatting, debugger event handling, or `DbgPrint` /
  `DbgTrace` buffer safety.
- Runtime behavior changes belong to `debug.c`, `dllmain.c`, or the project
  file, depending on whether the transition is debug runtime logic, startup
  ordering, or build-surface selection.
- Future changes to this header must prove the caller topology and concrete
  runtime owner before behavior claims.

## Topology

```text
dllmain.c
-> Debug_Wait
-> debug.c config reads
-> IsDebuggerPresent / OutputDebugString / Sleep / __debugbreak

SboxDll.vcxproj WITH_DEBUG
-> debug.h exposes Debug_Init
-> dllmain.c conditionally calls Debug_Init
-> debug.c optional debug hook scaffolding and disabled break-image block

SREV-146
-> debug.c DbgPrint / DbgTrace buffer termination
-> Windows WITH_DEBUG DLL build and debug-format runtime proof
```

The header is the declaration node. It is not the owner of Sandboxie policy,
debugger wait semantics, hook behavior, or debug-format memory safety.

## Logic Risk

The high coverage score comes from `debug.h` naming NT/debug/COM-adjacent
signals and a currently enabled `WITH_DEBUG` build surface. Patching the header
would be the wrong route unless the bug is declaration ownership itself.
Behavior reviews must target the executable owner where the boundary is crossed.

## Official Shape

Microsoft documents `IsDebuggerPresent` as a same-process user-mode debugger
query, `OutputDebugStringW` as debugger-output emission, `Sleep` as suspending
the current thread for an interval, and `DebugBreak` as causing a breakpoint
exception in the current process. Those APIs explain the debug-wait behavior in
`debug.c`; they do not make `debug.h` the owner of that behavior.

Official references:

- `https://learn.microsoft.com/en-us/windows/win32/api/debugapi/nf-debugapi-isdebuggerpresent`
- `https://learn.microsoft.com/en-us/windows/win32/api/debugapi/nf-debugapi-outputdebugstringw`
- `https://learn.microsoft.com/en-us/windows/win32/api/synchapi/nf-synchapi-sleep`
- `https://learn.microsoft.com/en-us/windows/win32/api/debugapi/nf-debugapi-debugbreak`

## Fix

No source patch. This SREV records `debug.h` as a declaration/topology header
and closes it as docs-only coverage. Future behavior patches should target the
owner that executes the relevant debugger wait, hook, output, startup, or build
transition.

## Acceptance Gate

`docs/plan/check-srev-236.py` validates the draft-07 schema, header declaration
shape, `debug.c` implementation topology, `dllmain.c` caller topology,
`SboxDll.vcxproj` build topology, existing SREV-146 owner coverage, split ledger
fragment, and absence of runtime owner code in this header.

Runtime/build gate: Windows `SboxDll` build continues to compile `debug.h` and
wire debug callers to `debug.c`; runtime behavior remains covered by existing
and future concrete-owner SREV Windows gates.
