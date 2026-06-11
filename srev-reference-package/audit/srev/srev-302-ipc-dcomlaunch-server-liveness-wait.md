# SREV-302: IPC DcomLaunch Server Liveness Wait

## Stage Gate

| Field | Value |
|---|---|
| Stage | data -> schema -> topology -> logic -> action -> verify |
| Input artifact | `Sandboxie/core/dll/ipc_start.c`, Microsoft process wait/exit-code references, SREV-010 |
| Output artifact | DcomLaunch second-stage wait liveness contract, draft-07 schema, targeted checker, ledger fragment |
| Owner | `Ipc_StartServer` |
| Acceptance gate | Targeted checker validates RpcSs process liveness remains in the DcomLaunch wait set, stale crash wording removal, official references, SREV-010 adjacency, and ledger fragment |

## Data

`Ipc_StartServer` starts `SandboxieRpcSs` for the `epmapper` port, waits for the
RpcSs server event, and then has a special DcomLaunch second-stage wait because
RpcSs signals its event before starting `SandboxieDcomLaunch`.

Before this SREV, the second-stage loop checked `hServerProcess` only while the
DcomLaunch `ServiceInitComplete` event could not yet be opened. Once that event
handle was opened, the code used only:

```text
WaitForSingleObject(hEvent, 30 * 1000)
```

If RpcSs exited after the DcomLaunch event handle was opened but before the
event was signaled, the wait loop could keep timing out and logging `-2` without
observing the server-process liveness edge.

## Official Shape

Microsoft documents `WaitForMultipleObjects` as waiting for any object in the
handle array when `bWaitAll` is `FALSE`. Event and process handles are both
valid wait handles. A return in the range `WAIT_OBJECT_0` to
`WAIT_OBJECT_0 + nCount - 1` identifies which handle was signaled; timeout and
failure have distinct return values.

Microsoft documents process termination as setting the process exit code and
signaling the process object. `GetExitCodeProcess` returns `STILL_ACTIVE` while
the process is still executing and returns the process exit code after
termination.

Microsoft documents `PROCESS_INFORMATION.hProcess` as the process handle
returned from process creation, and `CreateProcessW` says handles in
`PROCESS_INFORMATION` must be closed when no longer needed.

Official references:

- `https://learn.microsoft.com/en-us/windows/win32/api/synchapi/nf-synchapi-waitformultipleobjects`
- `https://learn.microsoft.com/en-us/windows/win32/procthread/terminating-a-process`
- `https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-getexitcodeprocess`
- `https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/ns-processthreadsapi-process_information`
- `https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-createprocessw`

## Schema

Local schema:

```text
docs/plan/srev-302-ipc-dcomlaunch-server-liveness-wait.schema.json
```

Contract id:

```text
IPC_DCOMLAUNCH_SERVER_LIVENESS_WAIT
```

## Topology

```text
RpcSs startup
  -> RpcSs server event signaled
  -> DcomLaunch second-stage event discovery
  -> DcomLaunch event wait plus RpcSs process liveness wait
  -> success when DcomLaunch event signals
  -> failure when RpcSs process signals before DcomLaunch event
```

SREV-302 owns only the DcomLaunch second-stage wait in `Ipc_StartServer`.
SREV-010 owns the unrelated UAC helper timeout boundary.

## Logic Risk

The old comment correctly noticed that `hServerProcess` should stay running, but
the code only enforced that while the DcomLaunch event handle was absent. After
the event handle existed, the process liveness edge was no longer in the wait
topology. A server crash in that window could leave the waiting thread in a
repeating timeout path instead of failing the startup route.

## Fix

The DcomLaunch event wait now uses `WaitForMultipleObjects` when
`hServerProcess` is available:

```text
DcomWaitHandles[0] = hEvent
DcomWaitHandles[1] = hServerProcess
```

`WAIT_OBJECT_0` still means the DcomLaunch event was signaled. `WAIT_OBJECT_0 +
1` means the RpcSs server process exited before DcomLaunch completed; the code
logs the existing `-4` failure and returns `FALSE`. When no process handle is
available, the existing single-event wait remains in place.

The pre-event `GetExitCodeProcess` probe is now gated by `hServerProcess`, so a
pre-existing RpcSs event path does not probe a null process handle.

No process launch policy, service selection, event naming, timeout length,
existing timeout log code, or handle-close ownership changed.

## Acceptance Gate

`docs/plan/check-srev-302.py` validates the draft-07 schema, official
references, source liveness comment, null-handle guard around
`GetExitCodeProcess`, DcomLaunch event/process `WaitForMultipleObjects`
topology, preserved single-event fallback, stale crash wording removal,
SREV-010 adjacency, combined ledger entry, and split ledger fragment.

Runtime gate: Windows RpcSs/DcomLaunch startup matrix covering normal startup,
RpcSs exit before the DcomLaunch event can be opened, RpcSs exit after the
DcomLaunch event is opened but before it signals, pre-existing RpcSs event with
no process handle, and OpenCOM / no-DcomLaunch cases.
