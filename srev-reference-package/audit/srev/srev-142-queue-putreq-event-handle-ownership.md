# SREV-142: Queue PutReq Event Handle Ownership

## Stage Gate

| Field | Value |
|---|---|
| Stage | action |
| Input artifact | `Sandboxie/core/dll/callsvc.c`, `Sandboxie/core/svc/queueserver.cpp`, `Sandboxie/core/svc/queuewire.h`, Microsoft event, duplicate-handle, and process-handle references |
| Output artifact | `docs/plan/srev-142-queue-putreq-event-handle-ownership.schema.json`, `docs/plan/check-srev-142.py`, `docs/plan/check-srev-142.sh`, ledger fragment |
| Owner | queue PutReq client/server event-handle transfer between `callsvc.c` and `queueserver.cpp` |
| Acceptance gate | targeted source checker plus core coverage/diff checkpoint; Windows runtime proof remains required for GUI/User proxy request/reply traffic |

## Evidence

`Sandboxie/core/svc/queueserver.cpp` was the highest-ranked unnamed reviewable
core file after SREV-141. Its queue `PutReq` path accepts a fixed wire packet
from the DLL, opens the caller process, duplicates the caller's event handle
into SbieSvc with `EVENT_MODIFY_STATE`, stores that duplicate in `REQUEST_OBJ`,
and signals the queue server when a request is available. Later, `PutRpl`
signals the duplicated client event so the original caller can wake and fetch
the reply.

The client packet is created by `SbieDll_QueuePutReqImpl` in
`Sandboxie/core/dll/callsvc.c`. Before this SREV, the function stored the event
handle only inside the allocated `QUEUE_PUTREQ_REQ` buffer, freed that buffer,
and then read `req->event_handle` on the failure cleanup path. That is a
use-after-free on a local request packet. On success, if the caller did not
request `out_EventHandle`, the original event handle also had no explicit local
owner after the request packet was freed.

Official references:

- https://learn.microsoft.com/en-us/windows/win32/api/synchapi/nf-synchapi-createeventw
- https://learn.microsoft.com/en-us/windows/win32/api/synchapi/nf-synchapi-setevent
- https://learn.microsoft.com/en-us/windows/win32/api/handleapi/nf-handleapi-duplicatehandle
- https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-openprocess
- https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-getprocesstimes
- https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-getexitcodeprocess

## Data

`QUEUE_PUTREQ_REQ.event_handle`, `QUEUE_PUTREQ_REQ.data_len`,
`SbieDll_QueuePutReqImpl`, `CreateEvent`, `SbieDll_CallServer`,
`out_RequestId`, `out_EventHandle`, `CloseHandle`, `QueueServer::PutReqHandler`,
`QueueServer::DuplicateEvent`, `NtOpenProcess`, `NtDuplicateObject`,
`EVENT_MODIFY_STATE`, `REQUEST_OBJ.client_event`, `SetEvent`, and
`DeleteRequestObj`.

## Schema

`QUEUE_PUTREQ_EVENT_HANDLE_OWNERSHIP` says:

- `callsvc.c` owns the caller's original event handle returned by
  `CreateEvent` until it is either transferred to `out_EventHandle` or closed.
- The allocated `QUEUE_PUTREQ_REQ` buffer is a wire packet, not the durable
  owner of the event handle after `Dll_Free(req)`.
- No cleanup path may read `req->event_handle` after `Dll_Free(req)`.
- `queueserver.cpp` owns only the duplicated service-side event handle returned
  by `NtDuplicateObject`.
- The service duplicate must request `EVENT_MODIFY_STATE` because the service
  later calls `SetEvent` on that handle.
- Failed `PutReq` calls close any caller-side event handle that was not
  transferred to the caller.
- Successful `PutReq` calls transfer the caller-side event handle only when
  `out_EventHandle` is non-null; otherwise the local owner closes it.

## Topology

Legal successful flow:

```text
SbieDll_QueuePutReqImpl
  -> CreateEvent creates caller-side event handle
  -> write handle value into QUEUE_PUTREQ_REQ.event_handle
  -> SbieDll_CallServer sends wire packet
  -> QueueServer::PutReqHandler opens caller process
  -> NtDuplicateObject duplicates event into SbieSvc with EVENT_MODIFY_STATE
  -> RequestObj.client_event owns service duplicate
  -> caller receives original EventHandle through out_EventHandle
  -> PutRplHandler signals service duplicate to wake caller wait
```

Legal failure or no-waiter flow:

```text
SbieDll_QueuePutReqImpl
  -> CreateEvent succeeds
  -> server call fails or caller did not request out_EventHandle
  -> Dll_Free(req)
  -> close local EventHandle variable
  -> never read the freed request packet
```

## Logic Risk

The request buffer and the event handle are different data owners. Treating the
buffer field as the post-free owner creates a use-after-free on error paths and
makes handle cleanup depend on freed packet memory. The fix is to keep a local
`HANDLE EventHandle` owner in the client function, copy its value into the wire
packet for the service, then either transfer that local handle to the caller or
close it after the packet is freed.

This SREV does not change queue naming, startup proxy selection, request id
generation, queue access policy, service-side duplicate access, or request/reply
payload routing.

## Fix

`SbieDll_QueuePutReqImpl` now stores the original event in a local
`EventHandle` variable. The wire packet receives the numeric handle value, but
cleanup no longer reads the packet after `Dll_Free(req)`. On success with
`out_EventHandle`, ownership transfers to the caller and the local variable is
cleared. On failure, or success without `out_EventHandle`, the remaining local
event handle is closed once.

`queueserver.cpp` behavior is unchanged. It still duplicates the caller event
into SbieSvc with `EVENT_MODIFY_STATE`, stores the duplicate in `REQUEST_OBJ`,
and closes that duplicate through request deletion.

## Acceptance Gate

`docs/plan/check-srev-142.py` validates the draft-07 schema, official reference
links, queue wire shape, client-side event ownership, absence of post-free
`req->event_handle` reads, service-side `NtDuplicateObject`/`EVENT_MODIFY_STATE`
routing, existing request cleanup, and the ledger fragment.
`docs/plan/check-srev-142.sh` is the targeted wrapper.

Runtime/build gate: Windows build; GUI/User proxy `SbieDll_QueuePutReq` success
path waits on the returned event and receives a reply; forced
`SbieDll_CallServer` failure closes the local event without use-after-free;
success with a null `out_EventHandle` does not leak the original event; service
duplicate cleanup still closes `REQUEST_OBJ.client_event`.
