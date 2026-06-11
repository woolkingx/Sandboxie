---
kind: srev-ledger-entry
id: SREV-021
title: UAC Slave Thread Handles Are Not Closed
status: patched-source-level-after-official-createthread-closehandle-handle-ownership-an
owner: "Sandboxie/core/svc/serviceserver2.cpp:909-917"
spec: docs/plan/srev-021-uac-thread-handle-ownership.md
schema: docs/plan/srev-021-uac-thread-handle-ownership.schema.json
checker: docs/plan/check-srev-021.sh
runtime_gate: run already-admin and dialog-approved UAC paths and verify no per-prompt thread-handle growth while cancellation and caller-exit behavior remain unchanged
---
### SREV-021: UAC Slave Thread Handles Are Not Closed

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | patched source-level after official `CreateThread` / `CloseHandle` handle ownership analysis; needs Windows UAC runtime proof |
| Evidence | `Sandboxie/core/svc/serviceserver2.cpp:909-917` and `serviceserver2.cpp:1036-1044` now close the thread handles returned for `RunUacSlave2Thread1` and `RunUacSlave2Thread2`; the previous source comments beside the `CreateThread` calls said `fix-me: i'm leaking a thread`. |
| Data | Thread handles returned by `CreateThread` for the two UAC helper workers. |
| Schema | `CreateThread` returns a caller-owned thread handle on success; `CloseHandle` closes the handle without terminating the associated thread. |
| Topology | `ServiceServer::RunUacSlave2` creates fire-and-forget helper threads inside the UAC helper process; no later local code waits on or signals the returned handles. |
| Logic Risk | Repeated UAC helper starts can leak kernel thread handles in the helper process, even though worker lifetime remains process-controlled. |
| Official Shape | `docs/plan/srev-021-uac-thread-handle-ownership.md` records Microsoft `CreateThread`, `CloseHandle`, and thread-creation example posture. |
| Fix | Both UAC creation branches now store each returned handle and close it immediately when non-NULL. The patch does not change worker entry points, prompt flow, or process lifetime. |
| Acceptance Gate | `docs/plan/check-srev-021.sh` proves the old leak comments are gone and both local `CreateThread` branches close `hThread1` and `hThread2`. Windows gate: run already-admin and dialog-approved UAC paths and verify no per-prompt thread-handle growth while cancellation and caller-exit behavior remain unchanged. |
