---
kind: srev-ledger-entry
id: SREV-302
title: IPC DcomLaunch Server Liveness Wait
status: patched-source-level-dcomlaunch-liveness-wait-needs-windows-runtime-proof
owner: Sandboxie/core/dll/ipc_start.c
spec: docs/plan/srev-302-ipc-dcomlaunch-server-liveness-wait.md
schema: docs/plan/srev-302-ipc-dcomlaunch-server-liveness-wait.schema.json
checker: docs/plan/check-srev-302.py
runtime_gate: Windows RpcSs/DcomLaunch startup matrix with server-exit timing windows and pre-existing-event negative control
---

### SREV-302: IPC DcomLaunch Server Liveness Wait

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level DcomLaunch liveness wait; needs Windows runtime proof |
| Evidence | `Ipc_StartServer` waits for `SandboxieRpcSs`, then performs a second-stage DcomLaunch wait because RpcSs signals its server event before starting `SandboxieDcomLaunch`. The previous code checked `hServerProcess` only before the DcomLaunch event handle could be opened. After that event handle existed, the loop waited only on `hEvent`; if RpcSs exited in that window, the loop could keep timing out and logging `-2`. The old source comment already admitted `hServerProcess` should stay running. |
| Data | `Ipc_StartServer`, `hServerEvent`, `hServerProcess`, `_rpcss`, `_dcomlaunch`, `Ipc_GetServerEvent`, `WaitForMultipleObjects`, `WaitForSingleObject`, `GetExitCodeProcess`, `STILL_ACTIVE`, `WAIT_OBJECT_0`, `SbieApi_Log(2204, ..., -4)`, and SREV-010. |
| Schema | `IPC_DCOMLAUNCH_SERVER_LIVENESS_WAIT` says `Ipc_StartServer` owns the RpcSs to DcomLaunch second-stage wait topology; `WaitForMultipleObjects` owns the event-or-process wait result when `hServerProcess` is available; `GetExitCodeProcess` probes are legal only when `hServerProcess` is non-null; RpcSs process termination before DcomLaunch event signal must fail the second-stage wait; SREV-010 owns the unrelated UAC helper timeout boundary. |
| Topology | `RpcSs startup -> RpcSs server event signaled -> DcomLaunch event discovery -> DcomLaunch event wait plus RpcSs process liveness wait -> success when DcomLaunch event signals -> failure when RpcSs process signals before DcomLaunch event`. |
| Logic Risk | The previous topology dropped the server-process liveness edge after the DcomLaunch event handle opened. That made one timing window vulnerable to repeated timeout logging rather than fail-closed startup failure when the process owner had already exited. |
| Official Shape | Microsoft documents `WaitForMultipleObjects` as waiting for any signaled handle when `bWaitAll` is false and allowing process and event handles in the wait array. Microsoft documents process termination as signaling the process object and changing the exit status from `STILL_ACTIVE` to the exit code. Microsoft documents `PROCESS_INFORMATION.hProcess` as the process handle returned by process creation and `CreateProcessW` handle close ownership. |
| Fix | The DcomLaunch event wait now uses a two-handle `WaitForMultipleObjects` when `hServerProcess` is available: index 0 is `hEvent`, index 1 is `hServerProcess`. Event signal preserves success. Process signal logs the existing `-4`, sets `bRet = FALSE`, and breaks. When no process handle is available, the existing single-event wait remains. The pre-event `GetExitCodeProcess` probe is now guarded by `hServerProcess`. No process launch policy, service selection, event naming, timeout length, existing timeout log code, or handle-close ownership changed. |
| Acceptance Gate | `docs/plan/check-srev-302.py` validates the draft-07 schema, official references, source liveness comment, null-handle guard around `GetExitCodeProcess`, DcomLaunch event/process `WaitForMultipleObjects` topology, preserved single-event fallback, stale crash wording removal, SREV-010 adjacency, combined ledger entry, and split ledger fragment; `docs/plan/check-srev-302.sh` is the targeted wrapper. Runtime gate: Windows RpcSs/DcomLaunch startup matrix covering normal startup, RpcSs exit before the DcomLaunch event can be opened, RpcSs exit after the DcomLaunch event is opened but before it signals, pre-existing RpcSs event with no process handle, and OpenCOM / no-DcomLaunch cases. |
