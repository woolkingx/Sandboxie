---
kind: srev-ledger-entry
id: SREV-217
title: EvtApi Internal Hook BOOL Contract
status: patched-source-level-after-official-getprocaddress-and-windows-data-type-review-needs-windows-runtime-proof
owner: Sandboxie/core/dll/event.c
declaration: Sandboxie/core/dll/dll.h
spec: docs/plan/srev-217-evtapi-internal-hook-bool-contract.md
schema: docs/plan/srev-217-evtapi-internal-hook-bool-contract.schema.json
checker: docs/plan/check-srev-217.py
runtime_gate: Windows DLL build plus a wevtapi.dll load smoke on supported Windows versions proving EvtApi_Init succeeds when the export is present, fails cleanly when the export is absent, and the installed detour still returns success with GetLastError() == 0.
---

### SREV-217: EvtApi Internal Hook BOOL Contract

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official `GetProcAddress` and Windows data type review; needs Windows runtime proof |
| Evidence | `Sandboxie/core/dll/event.c` was the top unnamed reviewable core file after SREV-216. It owns Sandboxie's `wevtapi.dll` hook for the internal `EvtIntAssertConfig` export. The export is internal and does not have a public Microsoft function page, so the local resolved-function typedef is the best available local ABI evidence: `P_EvtIntAssertConfig` returns `BOOL`. Before this fix, the replacement function was declared and defined as returning `BOOLEAN`. Microsoft documents `BOOL` as `int` and `BOOLEAN` as `BYTE`, so this is not the same return-width contract. `EvtApi_Init` also passed the resolved export pointer into `SBIEDLL_HOOK` without first proving `GetProcAddress` succeeded. |
| Data | `event.c`, `dll.h`, `ldr.c`, `EvtApi_Init`, `EvtIntAssertConfig`, `Event_EvtIntAssertConfig`, `P_EvtIntAssertConfig`, `GetProcAddress`, `SBIEDLL_HOOK`, `__sys_EvtIntAssertConfig`, `BOOL`, `BOOLEAN`, `SetLastError`, and `wevtapi.dll`. |
| Schema | `EVTAPI_INTERNAL_HOOK_BOOL_CONTRACT` says `event.c` owns the `wevtapi.dll!EvtIntAssertConfig` hook; the internal export has no public Microsoft API page and local ABI evidence is the `P_EvtIntAssertConfig` typedef; the local typedef and detour must both return `BOOL`; `EvtApi_Init` must not call `SBIEDLL_HOOK` unless `GetProcAddress` returned a non-null export pointer; and the detour policy remains "return success and clear last error". |
| Topology | Legal flow is `wevtapi.dll -> GetProcAddress("EvtIntAssertConfig") -> non-null gate -> P_EvtIntAssertConfig BOOL ABI -> SBIEDLL_HOOK original-function storage -> Event_EvtIntAssertConfig BOOL detour -> SetLastError(0), TRUE`. |
| Logic Risk | The hook is a binary ABI boundary. Returning `BOOLEAN` exposes only one byte of the result shape, while the local function-pointer contract says the replaced function returns Win32 `BOOL`. The code also treated an unresolved internal export as if it were hookable. That is risky for an internal function whose presence may vary by Windows build. |
| Official Shape | `docs/plan/srev-217-evtapi-internal-hook-bool-contract.md` records Microsoft `GetProcAddress` and Windows data type references. `docs/plan/srev-217-evtapi-internal-hook-bool-contract.schema.json` records the JSON Schema draft-07 local `EVTAPI_INTERNAL_HOOK_BOOL_CONTRACT` contract. |
| Fix | `event.c` now declares and defines `Event_EvtIntAssertConfig` with `BOOL`. `EvtApi_Init` now returns `FALSE` before hook installation if `GetProcAddress(module, "EvtIntAssertConfig")` returns `NULL`. The `SetLastError(0)` and `TRUE` detour policy, selected export name, loader registration, and `SBIEDLL_HOOK` ownership remain unchanged. |
| Acceptance Gate | `docs/plan/check-srev-217.py` validates the draft-07 schema, official references, local `BOOL` typedef/detour alignment, `GetProcAddress` non-null gate before `SBIEDLL_HOOK`, unchanged success policy, split ledger fragment, and removal of the stale `BOOLEAN` detour return shape; `docs/plan/check-srev-217.sh` is the targeted wrapper. Runtime/build gate: Windows DLL build plus a `wevtapi.dll` load smoke on supported Windows versions proving `EvtApi_Init` succeeds when the export is present, fails cleanly when the export is absent, and the installed detour still returns success with `GetLastError() == 0`. |
