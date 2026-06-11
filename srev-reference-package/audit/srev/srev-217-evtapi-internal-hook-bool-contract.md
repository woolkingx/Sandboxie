# SREV-217: EvtApi Internal Hook BOOL Contract

## Stage

schema -> boundary -> topology -> logic -> action -> verify

## Evidence

`Sandboxie/core/dll/event.c` was the top unnamed reviewable core file after
SREV-216. It owns Sandboxie's `wevtapi.dll` hook for the internal
`EvtIntAssertConfig` export. `ldr.c` loads `wevtapi.dll` through
`EvtApi_Init` with the local comment "disable EvtIntAssertConfig". `event.c`
resolves `EvtIntAssertConfig` by name and installs a replacement through
`SBIEDLL_HOOK`.

The export is internal and does not have a public Microsoft function page, so
the local resolved-function typedef is the best available local ABI evidence:
`P_EvtIntAssertConfig` returns `BOOL`. Before this fix, the replacement
function was declared and defined as returning `BOOLEAN`. Microsoft documents
`BOOL` as `int` and `BOOLEAN` as `BYTE`, so this is not the same return-width
contract. `EvtApi_Init` also passed the resolved export pointer into
`SBIEDLL_HOOK` without first proving `GetProcAddress` succeeded.

## Data

`event.c`, `dll.h`, `ldr.c`, `EvtApi_Init`, `EvtIntAssertConfig`,
`Event_EvtIntAssertConfig`, `P_EvtIntAssertConfig`, `GetProcAddress`,
`SBIEDLL_HOOK`, `__sys_EvtIntAssertConfig`, `BOOL`, `BOOLEAN`, `SetLastError`,
and `wevtapi.dll`.

## Official Shape

Microsoft documents `GetProcAddress` as returning an exported function address
on success and `NULL` on failure. It also advises applications that use an
export that might not exist to resolve by name and handle the unavailable case.

Microsoft documents Windows data types: `BOOL` is `typedef int BOOL`, while
`BOOLEAN` is `typedef BYTE BOOLEAN`. A hook wrapper must use the same return
type as the local resolved-function typedef it is replacing.

References:

- `https://learn.microsoft.com/en-us/windows/win32/api/libloaderapi/nf-libloaderapi-getprocaddress`
- `https://learn.microsoft.com/en-us/windows/win32/winprog/windows-data-types`

## Schema

`EVTAPI_INTERNAL_HOOK_BOOL_CONTRACT` says:

- `event.c` owns the `wevtapi.dll!EvtIntAssertConfig` hook.
- The internal export has no public Microsoft API page; local ABI evidence is
  the `P_EvtIntAssertConfig` typedef.
- The local typedef and detour must both return `BOOL`.
- `EvtApi_Init` must not call `SBIEDLL_HOOK` unless `GetProcAddress` returned a
  non-null export pointer.
- The detour policy remains "return success and clear last error".

## Topology

```text
wevtapi.dll
-> GetProcAddress("EvtIntAssertConfig")
-> non-null gate
-> P_EvtIntAssertConfig BOOL ABI
-> SBIEDLL_HOOK original-function storage
-> Event_EvtIntAssertConfig BOOL detour
-> SetLastError(0), TRUE
```

## Logic Risk

The hook is a binary ABI boundary. Returning `BOOLEAN` exposes only one byte of
the result shape, while the local function-pointer contract says the replaced
function returns Win32 `BOOL`. The code also treated an unresolved internal
export as if it were hookable. That is risky for an internal function whose
presence may vary by Windows build.

## Fix

`event.c` now declares and defines `Event_EvtIntAssertConfig` with `BOOL`.
`EvtApi_Init` now returns `FALSE` before hook installation if
`GetProcAddress(module, "EvtIntAssertConfig")` returns `NULL`.

The `SetLastError(0)` and `TRUE` detour policy, selected export name, loader
registration, and `SBIEDLL_HOOK` ownership remain unchanged.

## Acceptance Gate

`docs/plan/check-srev-217.py` validates the draft-07 schema, official
references, local `BOOL` typedef/detour alignment, `GetProcAddress` non-null
gate before `SBIEDLL_HOOK`, unchanged success policy, split ledger fragment,
and removal of the stale `BOOLEAN` detour return shape.

Runtime/build gate: Windows DLL build plus a `wevtapi.dll` load smoke on
supported Windows versions proving `EvtApi_Init` succeeds when the export is
present, fails cleanly when the export is absent, and the installed detour still
returns success with `GetLastError() == 0`.
