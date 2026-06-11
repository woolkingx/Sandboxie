# SREV-191 Named Pipe Pending I/O Lifetime Contract

| Field | Content |
|---|---|
| Stage | schema -> boundary -> action -> verify |
| Input Artifact | `Sandboxie/core/svc/namedpipeserver.cpp`, `Sandboxie/core/svc/namedpipeserver.h`, `Sandboxie/core/svc/namedpipewire.h`, and `Sandboxie/core/svc/ProxyHandle.cpp`. |
| Output Artifact | Draft-07 schema, source checker, split ledger fragment, and source readback proving pending named-pipe I/O cannot outlive its stack `IO_STATUS_BLOCK`, request buffer, reply buffer, or shared completion event ownership. |
| Owner | `Sandboxie/core/svc/namedpipeserver.cpp` owns the service-side named-pipe proxy handle, completion event, and `NtReadFile` / `NtWriteFile` pending I/O lifetime. |
| Acceptance Gate | `docs/plan/check-srev-191.py`, `docs/plan/check-srev-191.sh`, core coverage, full SREV/KPATH matrix, and `git diff --check`. |

## Data

`NamedPipeServer::ReadHandler` and `NamedPipeServer::WriteHandler` issue
`NtReadFile` and `NtWriteFile` with:

- `ProxyPipe->hPipe` as the named-pipe handle;
- `ProxyPipe->hEvent` as the completion event;
- a stack `IO_STATUS_BLOCK`;
- `rpl->data` for read output;
- `req->data` for write input;
- a 10 second wait before timeout handling.

The old timeout path called `CancelIo(ProxyPipe->hPipe)`, wrote local cancelled
status into the stack `IO_STATUS_BLOCK`, and returned to the caller immediately.
That returned while the kernel/provider could still own the pending I/O request,
the supplied `IO_STATUS_BLOCK`, and the transfer buffer.

The same proxy handle also reused one auto-reset event for every operation on
that named-pipe handle. Without an owner-local serialization gate, two service
worker threads could issue concurrent operations using the same event and make a
completion signal ambiguous.

## Official API Shape

Microsoft documents `NtReadFile` and `NtWriteFile` as receiving caller-supplied
`IO_STATUS_BLOCK` and buffer pointers, with an optional event set after
completion. The `IO_STATUS_BLOCK` documentation says when a routine returns
`STATUS_PENDING`, the caller should wait for completion and then check the
`IO_STATUS_BLOCK` for the final status.

Microsoft documents `CancelIo` and `CancelIoEx` as requesting cancellation, not
as proving completion. `CancelIoEx` explicitly says the application must not
free or reuse the overlapped structure until the operation has completed, and
that cancellation does not wait for all canceled operations to complete.

Microsoft documents `ReadFile` and `WriteFile` buffer lifetime in the same
direction: the buffer must remain valid and must not be read, written,
reallocated, or freed while the I/O operation is still using it.

Microsoft documents `CreateEvent` auto-reset behavior: if no thread is waiting,
the event can remain signaled until a waiter is released. `ResetEvent` explicitly
sets an event to the nonsignaled state. A reused per-handle event therefore
needs a single-operation owner and a reset-before-issue gate so a stale signal
cannot be mistaken for the current operation.

Official references:

- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/nf-ntifs-ntreadfile`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/nf-ntifs-ntwritefile`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/ns-wdm-_io_status_block`
- `https://learn.microsoft.com/en-us/windows/win32/fileio/cancelio`
- `https://learn.microsoft.com/en-us/windows/win32/fileio/cancelioex-func`
- `https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-readfile`
- `https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-writefile`
- `https://learn.microsoft.com/en-us/windows/win32/api/synchapi/nf-synchapi-createeventw`
- `https://learn.microsoft.com/en-us/windows/win32/api/synchapi/nf-synchapi-resetevent`

## Boundary

The boundary is:

```text
sandboxed process named-pipe request
-> SbieSvc NamedPipeServer proxy handle
-> host named-pipe NtReadFile / NtWriteFile
-> completion event and IO_STATUS_BLOCK
-> SbieSvc reply wire
```

At this boundary, SbieSvc owns every pointer passed to `NtReadFile` and
`NtWriteFile` until the operation completes. A timeout only changes the local
policy decision; it does not transfer lifetime ownership away from the pending
I/O request.

## Topology

The legal topology is:

```text
proxy handle
-> per-handle I/O lock
-> ResetEvent(hEvent)
-> NtReadFile / NtWriteFile
-> if STATUS_PENDING: bounded wait
-> if timeout: CancelIo request
-> wait until completion event
-> normal completion reads final IO_STATUS_BLOCK
-> timeout completion maps local reply to STATUS_CANCELLED and zero bytes
-> release lock and reply
```

The per-handle I/O lock is not a global broker lock. It only prevents two
operations on one proxied named-pipe handle from sharing the same event and
completion state at the same time.

## Logic Risk

`CancelIo` is a cancellation request, not a completion proof. Returning from
`ReadHandler` or `WriteHandler` immediately after `CancelIo` can let the
function return while the provider still has a pointer to a stack
`IO_STATUS_BLOCK` or to a request/reply buffer owned by the service message.
That is a use-after-return/use-after-free class bug.

The shared event is a second correctness node. With concurrent read/write
requests on the same proxy handle, a single event can signal completion of a
different pending request. That can make one handler read the wrong
`IO_STATUS_BLOCK` or release buffers before the actual request completes.

## Fix

- `PROXY_PIPE` owns a per-handle `CRITICAL_SECTION` pointer for named-pipe file
  operations.
- `OpenHandler` allocates and initializes the lock before publishing the proxy
  handle; `CloseCallback` deletes and frees it.
- `ReadHandler` and `WriteHandler` enter the per-handle I/O lock around event
  reset, native I/O issue, pending wait, timeout cancellation, completion wait,
  and final status extraction.
- Pending read/write timeout now requests `CancelIo`, then waits for the same
  event before mapping the local reply to `STATUS_CANCELLED` with zero transfer
  bytes.
- `ResetEvent` runs before each native read/write issue while the lock is held,
  preventing a stale auto-reset event signal from satisfying the new wait.

No named-pipe allow-list, wire message layout, request length gate, reply length
gate, LPC/ALPC path, or driver API was changed.

## Runtime Gate

Linux source checks prove the local lifetime topology and stale cancel path
removal. A Windows gate remains required: build SbieSvc, run named-pipe read and
write through the proxy, run concurrent read/write requests on the same proxy
handle, run timeout/cancel smoke with a blocked peer, and verify no stale event,
wrong completion, stack corruption, nonzero timeout payload, or service-wide
deadlock.
