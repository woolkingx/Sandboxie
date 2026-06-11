---
kind: srev-ledger-entry
id: SREV-198
title: SCM Notify APC Contract
status: patched-source-level-after-official-scm-apc-shape-review-needs-windows-runtime-proof
owner: Sandboxie/core/dll/scm_notify.c
spec: docs/plan/srev-198-scm-notify-apc-contract.md
schema: docs/plan/srev-198-scm-notify-apc-contract.schema.json
checker: docs/plan/check-srev-198.py
runtime_gate: Windows DLL build plus SCM notification callback, re-registration, APC failure, wait timeout, cancel, and success smoke
---

### SREV-198: SCM Notify APC Contract

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official SCM/APC shape review; needs Windows runtime proof |
| Evidence | `Sandboxie/core/dll/scm_notify.c` was the top unnamed reviewable core file after SREV-197. Before this fix, `Scm_NotifyServiceStatusChangeW` dereferenced `pNotifyBuffer` before validating it, did not validate `pfnNotifyCallback`, could return `ERROR_SUCCESS` even when watcher event/thread creation failed, did not refresh `data`/`mask` when re-registering an existing service handle, ignored `QueueUserAPC` failure, and `Scm_WaitServiceState` returned `ss->dwCurrentState` after freeing the reply buffer that owned `ss`. |
| Data | `NotifyServiceStatusChangeW`, `SERVICE_NOTIFY`, `pfnNotifyCallback`, `dwNotifyMask`, `OpenThread(THREAD_SET_CONTEXT)`, `CreateEvent`, `CreateThread`, `QueueUserAPC`, `SERVICE_QUERY_RPL`, and `SERVICE_STATUS_PROCESS.dwCurrentState`. |
| Schema | `SCM_NOTIFY_APC_CONTRACT` says the caller's `SERVICE_NOTIFY` buffer and callback pointer must be validated before storage/callback, watcher resources must be checked before returning success, re-registration must publish the current buffer and mask, APC enqueue success must gate inactive transition, and wait-state return values must be copied before freeing the broker reply. |
| Topology | Legal flow is `caller thread + SERVICE_NOTIFY buffer -> Sandboxie SCM notify hook -> service-status broker poll -> QueueUserAPC(caller thread, caller buffer) -> caller callback`. The caller owns the buffer under the Windows lifetime rule; `scm_notify.c` owns only the local hook list and watcher handles. |
| Logic Risk | The old source could crash on a null notify buffer, call through a null callback, acknowledge a notification request that had no functioning watcher, leave later requests pointing at stale buffers/masks, silently lose a notification if APC enqueue failed, and read freed reply memory when returning a reached service state. |
| Official Shape | `docs/plan/srev-198-scm-notify-apc-contract.md` records Microsoft `NotifyServiceStatusChangeW`, `SERVICE_NOTIFY_2W`, `OpenThread`, `QueueUserAPC`, `CreateEventW`, `CreateThread`, `WaitForMultipleObjects`, and `GetTickCount` references. `docs/plan/srev-198-scm-notify-apc-contract.schema.json` records the JSON Schema draft-07 local `SCM_NOTIFY_APC_CONTRACT` contract. |
| Fix | `scm_notify.c` now rejects null notify buffers, null callbacks, and zero masks before registration; checks global/element allocation, `OpenThread`, `CreateEvent`, and `CreateThread` before success; cleans up a newly inserted element on watcher-resource failure; refreshes `data` and `mask` on each registration; marks a notification inactive only after `QueueUserAPC` succeeds; checks the callback pointer in the APC dispatcher; and returns a copied `current_state` from `Scm_WaitServiceState`. |
| Acceptance Gate | `docs/plan/check-srev-198.py` validates the draft-07 schema, official references, registration gates, watcher failure gates, existing-entry update, APC enqueue gate, callback pointer gate, copied wait-state return, and split ledger fragment; `docs/plan/check-srev-198.sh` is the targeted wrapper. Runtime/build gate: Windows DLL build plus SCM notification callback, re-registration, APC failure or target-thread-exit fault injection, wait timeout, cancel, and success smoke. |
