---
kind: srev-ledger-entry
id: SREV-023
title: Legacy LPC Disconnect Treats Dead Thread Object As Live
status: patched-source-level-after-official-thread-object-liveness-analysis-needs-window
owner: "Sandboxie/core/svc/PipeServer.cpp:738-745"
spec: docs/plan/srev-023-pipeserver-thread-liveness.md
schema: docs/plan/srev-023-pipeserver-thread-liveness.schema.json
checker: docs/plan/check-srev-023.sh
runtime_gate: legacy LPC close-by-create-time removes dead thread entries while retaining live same-process threads
---
### SREV-023: Legacy LPC Disconnect Treats Dead Thread Object As Live

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | patched source-level after official thread-object liveness analysis; needs Windows Vista legacy LPC runtime proof |
| Evidence | `Sandboxie/core/svc/PipeServer.cpp:738-745` opened a thread and only checked `GetProcessIdOfThread`; `PipeServer.cpp:749-750` said closing the port shortly after thread termination can fail and leave the client object uncleared. |
| Data | Stored legacy LPC client process/thread ids and per-thread port state. |
| Schema | A thread id/handle association is not the same as liveness; after termination the thread object becomes signaled and can remain valid until handles close. |
| Topology | `PortDisconnectByCreateTime` receives a port-close message without CID, maps by process create time, then chooses a stale client thread to pass into `PortDisconnectHelper`. |
| Logic Risk | A just-terminated but still-openable thread object can be retained as live, preventing stale client-thread/process cleanup. |
| Official Shape | `docs/plan/srev-023-pipeserver-thread-liveness.md` records Microsoft `GetProcessIdOfThread`, thread termination/object lifetime, and `WaitForSingleObject` zero-timeout semantics. |
| Fix | The liveness gate now opens with `THREAD_QUERY_INFORMATION | SYNCHRONIZE`, checks the process id, and keeps the client only when `WaitForSingleObject(hThread, 0)` returns `WAIT_TIMEOUT`. Signaled, failed-wait, missing, or mismatched threads are stale. |
| Acceptance Gate | `docs/plan/check-srev-023.sh` proves the old fix-me is gone and the cleanup path uses process-id plus thread-object nonsignaled state. Windows gate: legacy LPC close-by-create-time removes dead thread entries while retaining live same-process threads. |
