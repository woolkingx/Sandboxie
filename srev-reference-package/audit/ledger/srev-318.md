---
kind: srev-ledger-entry
id: SREV-318
title: Ldr NtTerminateProcess Disabled Hook Boundary
status: patched comment/topology for disabled NtTerminateProcess notification-cookie cleanup; no behavior change
owner: Sandboxie/core/dll/ldr.c
spec: docs/plan/srev-318-ldr-ntterminateprocess-disabled-hook-boundary.md
schema: docs/plan/srev-318-ldr-ntterminateprocess-disabled-hook-boundary.schema.json
checker: docs/plan/check-srev-318.py
runtime_gate: Windows ARM64/ARM64EC process-exit matrix before enabling the disabled NtTerminateProcess hook
---

### SREV-318: Ldr NtTerminateProcess Disabled Hook Boundary

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | patched comment/topology for disabled `NtTerminateProcess` notification-cookie cleanup; no behavior change |
| Evidence | On Windows 8.1 and later, `Ldr_Init` resolves `LdrRegisterDllNotification` and `LdrUnregisterDllNotification`, registers `Ldr_LdrDllNotification`, and stores the callback identifier in `LdrLoaderCookie`. A commented-out `Ldr_NtTerminateProcess` body would call `LdrUnregisterDllNotification(LdrLoaderCookie)` before forwarding to native `NtTerminateProcess`, but the hook remains disabled. The old comment only said `Todo: Fix-Me` and reported an ARM64 hang symptom. |
| Data | `Ldr_Init`, `LdrRegisterDllNotification`, `LdrUnregisterDllNotification`, `LdrDllNotification`, `LdrLoaderCookie`, `Ldr_NtTerminateProcess`, `NtTerminateProcess`, `Ldr_Win10_LdrLoadDll`, SREV-312, ARM64, and ARM64EC. |
| Schema | `LDR_NTTERMINATEPROCESS_DISABLED_HOOK_BOUNDARY` says `LdrRegisterDllNotification` returns a callback identifier cookie used for unregister; `LdrUnregisterDllNotification` owns cancellation of the registered DLL notification cookie; `LdrDllNotification` callback context is constrained and unsafe for broad cross-module calls; `TerminateProcess` is unconditional process termination and may compromise DLL global state; the `NtTerminateProcess` hook remains disabled until ARM64 process-exit runtime proof exists; this SREV changes comments and proof only, not notification registration, unregister behavior, or hook activation. |
| Topology | Active path: `Windows 8.1+ -> Ldr_Init -> GetProcAddress(LdrRegisterDllNotification/LdrUnregisterDllNotification) -> LdrRegisterDllNotification(..., &LdrLoaderCookie) -> Ldr_LdrDllNotification -> SREV-312 loader notification dispatch -> SBIEDLL_HOOK(Ldr_Win10_, LdrLoadDll)`. Disabled path: `NtTerminateProcess hook -> Ldr_NtTerminateProcess -> current-process termination gate -> LdrUnregisterDllNotification(LdrLoaderCookie) -> native NtTerminateProcess`. |
| Logic Risk | The stale TODO hid the real owner boundary: enabling the hook crosses process termination, notification-cookie unregister, and loader-callback constraints at the same time. The next legal step is ARM64/ARM64EC process-exit runtime proof and call capture, not simply uncommenting the hook. |
| Official Shape | Microsoft documents `LdrRegisterDllNotification` as returning a callback identifier cookie, `LdrUnregisterDllNotification` as cancelling a registered notification by cookie, `LdrDllNotification` as an early loader callback with cross-module call restrictions, and `TerminateProcess` as unconditional termination that can compromise DLL-maintained global state. |
| Fix | Comment-only source clarification. The disabled `NtTerminateProcess` hook is now labeled as SREV-318 notification-cookie cleanup that remains disabled until ARM64 process-exit runtime proof exists. No `LdrRegisterDllNotification`, `LdrUnregisterDllNotification`, `LdrLoaderCookie`, disabled `Ldr_NtTerminateProcess` body, `NtTerminateProcess` hook, or `Ldr_Win10_LdrLoadDll` hook behavior changed. |
| Acceptance Gate | `docs/plan/check-srev-318.py` validates the draft-07 schema, official references, active notification registration, inactive unregister and `NtTerminateProcess` hook body, updated source comment, stale TODO/Fix-Me/hang wording removal from the hook-selection block, unchanged `Ldr_Win10_LdrLoadDll` hook, SREV-312 adjacency, combined ledger entry, and split ledger fragment; `docs/plan/check-srev-318.sh` is the targeted wrapper. Runtime gate: Windows ARM64/ARM64EC process-exit matrix before enabling the disabled hook: normal self-exit, `TerminateProcess` self-termination, out-of-process termination, DLL load/unload during shutdown, and negative controls proving no process hang and no loader notification regression. |
