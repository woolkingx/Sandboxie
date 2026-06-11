---
kind: srev-ledger-entry
id: SREV-203
title: GUI Window Hook Register Lock Exit
status: patched-source-level-after-official-critical-section-thread-handle-shape-review-needs-windows-runtime-proof
owner: Sandboxie/core/svc/GuiServer.h
implementation: Sandboxie/core/svc/GuiServer.cpp
spec: docs/plan/srev-203-gui-wnd-hook-register-lock-exit.md
schema: docs/plan/srev-203-gui-wnd-hook-register-lock-exit.schema.json
checker: docs/plan/check-srev-203.py
runtime_gate: Windows service build plus malformed/stale GUI_WND_HOOK_REGISTER request smoke proving subsequent GUI proxy requests do not hang behind m_SlavesLock
---

### SREV-203: GUI Window Hook Register Lock Exit

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official critical-section/thread-handle shape review; needs Windows runtime proof |
| Evidence | `Sandboxie/core/svc/GuiServer.h` was the top unnamed reviewable core file after SREV-202. Its implementation in `Sandboxie/core/svc/GuiServer.cpp` owns GUI proxy request dispatch and the `GUI_WND_HOOK_REGISTER` path. Before this fix, `WndHookRegisterSlave` entered `m_SlavesLock` and then returned directly on `OpenThread` failure or thread-owner mismatch, skipping `LeaveCriticalSection`. The same path allocated a new `WND_HOOK` entry without checking `HeapAlloc`. |
| Data | `GUI_WND_HOOK_REGISTER_REQ`, `GUI_WND_HOOK_REGISTER_RPL`, `m_SlavesLock`, `m_WndHooks`, `WND_HOOK`, `req->hthread`, `req->hproc`, `args->pid`, `OpenThread`, `GetProcessIdOfThread`, `CloseHandle`, `HeapAlloc`, `List_Insert_After`, and `LeaveCriticalSection`. |
| Schema | `GUI_WND_HOOK_REGISTER_LOCK_EXIT` says every exit after `EnterCriticalSection(&m_SlavesLock)` must pass through `LeaveCriticalSection(&m_SlavesLock)`; `OpenThread` failure and owner mismatch preserve the existing outer failure status only after releasing the lock; a successful thread handle is closed before owner mismatch failure; a new `WND_HOOK` is inserted only after allocation succeeds; and successful register/unregister reply shape is preserved. |
| Topology | Legal flow is `GUI_WND_HOOK_REGISTER request -> fixed-size wire gate -> EnterCriticalSection -> find caller WND_HOOK -> OpenThread/GetProcessIdOfThread/CloseHandle -> owner gate -> HeapAlloc WND_HOOK if needed -> List_Insert_After or HookCount update -> LeaveCriticalSection -> success reply or preserved failure status`. |
| Logic Risk | The old direct returns could leave the GUI slave lock owned after a malformed or stale hook-register request, causing later GUI proxy requests to hang behind `m_SlavesLock` while the process remained alive. The unchecked allocation could also crash while the lock was held. |
| Official Shape | `docs/plan/srev-203-gui-wnd-hook-register-lock-exit.md` records Microsoft `EnterCriticalSection`, `LeaveCriticalSection`, `OpenThread`, `GetProcessIdOfThread`, `CloseHandle`, and `HeapAlloc` references. `docs/plan/srev-203-gui-wnd-hook-register-lock-exit.schema.json` records the JSON Schema draft-07 local `GUI_WND_HOOK_REGISTER_LOCK_EXIT` contract. |
| Fix | `WndHookRegisterSlave` now stores failure status, routes all post-lock failure exits through a `finish` label, releases `m_SlavesLock` before returning the preserved failure status, checks `HeapAlloc` before writing a new `WND_HOOK`, and keeps successful reply behavior unchanged. |
| Acceptance Gate | `docs/plan/check-srev-203.py` validates the draft-07 schema, official references, header/implementation owner coordinates, single-exit lock shape, stale direct returns removal from the locked region, `CloseHandle` before owner mismatch failure, allocation failure handling, and split ledger fragment; `docs/plan/check-srev-203.sh` is the targeted wrapper. Runtime/build gate: Windows service build plus malformed/stale `GUI_WND_HOOK_REGISTER` request smoke proving subsequent GUI proxy requests do not hang behind `m_SlavesLock`. |
