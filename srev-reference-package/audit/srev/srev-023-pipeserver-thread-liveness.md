# SREV-023: PipeServer Thread Liveness Cleanup

## Stage Gate

| Field | Content |
|---|---|
| Stage | schema -> topology -> logic -> action |
| Input Artifact | Legacy LPC `PortDisconnectByCreateTime` cleanup path |
| Output Artifact | Source-level liveness gate plus `docs/plan/check-srev-023.sh` |
| Owner | `PipeServer::PortDisconnectByCreateTime` |
| Acceptance Gate | A client thread is retained only when its thread object is still nonsignaled and still belongs to the recorded process id. |

## Official Shape

Microsoft `GetProcessIdOfThread` documentation says the function returns the
process identifier associated with a thread handle:

```text
https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-getprocessidofthread
```

Microsoft thread lifecycle documentation says a thread object's state becomes
signaled when the thread terminates, and the thread object is not freed until
all open handles are closed:

```text
https://learn.microsoft.com/en-us/windows/win32/procthread/terminating-a-thread
https://learn.microsoft.com/en-us/windows/win32/procthread/thread-handles-and-identifiers
```

Microsoft `WaitForSingleObject` documentation says a zero timeout checks the
object state and returns immediately; waiting on a thread handle requires the
`SYNCHRONIZE` access right:

```text
https://learn.microsoft.com/en-us/windows/win32/api/synchapi/nf-synchapi-waitforsingleobject
```

## Local Shape

The Vista legacy LPC disconnect path can receive a port-closed message with no
CID and only a process creation timestamp. `PortDisconnectByCreateTime` finds
the matching process and scans its stored client threads.

The old liveness test retained a stored client thread if:

1. `OpenThread(THREAD_QUERY_INFORMATION, ...)` succeeded; and
2. `GetProcessIdOfThread` matched the stored process id.

That proves the thread handle still names a thread object associated with the
same process, but it does not prove the thread is still running. A just-exited
thread can still have a valid object until all handles close.

## Finding

The inline source comment said that closing the port shortly after thread
termination can fail and leave the client object uncleared. The local cause is
that a terminated-but-still-openable thread object was treated as live.

## Fix

The liveness gate now opens the thread with `THREAD_QUERY_INFORMATION |
SYNCHRONIZE`, checks the process id, and keeps the client only when
`WaitForSingleObject(hThread, 0)` returns `WAIT_TIMEOUT`. A signaled thread
object, a failed wait, a missing thread, or a process-id mismatch is treated as
stale and routed to existing `PortDisconnectHelper` cleanup.

## Runtime Gate

Windows runtime proof:

1. legacy LPC close-by-create-time path removes a thread entry after the client
   thread exits;
2. a still-running thread in the same process is retained;
3. process-level cleanup still fires when the last thread entry is removed;
4. normal broker requests are unaffected.
