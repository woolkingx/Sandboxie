# SREV-207: Queue Name Wire Copy Contract

## Stage

schema -> boundary -> topology -> logic -> action -> verify

## Evidence

`Sandboxie/core/svc/queueserver.h` was the top unnamed reviewable core file
after SREV-206. It declares the `QueueServer` owner for fixed queue wire
messages and the `MakeQueueName` / `FindQueueObj` name boundary. The server wire
schema in `queuewire.h` fixes queue names at `QUEUE_NAME_MAXLEN` WCHARs.

Before this fix, the exported DLL queue helpers in
`Sandboxie/core/dll/callsvc.c` copied caller-supplied queue names into those
fixed wire fields with `wcscpy`. A queue name with 64 or more WCHARs could
overflow stack or heap request packets before the request reached
`QueueServer::MakeQueueName`, so the server-side truncation guard was too late
for the client wire boundary.

## Data

`queueserver.h`, `QueueServer`, `MakeQueueName`, `FindQueueObj`,
`queuewire.h`, `QUEUE_NAME_MAXLEN`, `QUEUE_CREATE_REQ.queue_name`,
`QUEUE_GETREQ_REQ.queue_name`, `QUEUE_PUTRPL_REQ.queue_name`,
`QUEUE_PUTREQ_REQ.queue_name`, `QUEUE_GETRPL_REQ.queue_name`,
`SbieDll_QueueCreate`, `SbieDll_QueueGetReq`, `SbieDll_QueuePutRpl`,
`SbieDll_QueuePutReqImpl`, `SbieDll_StartProxy`, `SbieDll_QueueGetRpl`,
`SbieDll_QueueCopyName`, `Dll_Alloc`, and `STATUS_INVALID_PARAMETER`.

## Official Shape

Microsoft documents `wcscpy` as copying the source string including the
terminating null and returning no error indicator. It also documents that
`wcscpy` does not check destination capacity and can cause buffer overruns.

Microsoft's buffer-overrun guidance names unchecked `wcscpy` copies as a source
of corruption and says external input must be validated and failed gracefully.

Microsoft documents `StringCchCopyW` as the bounded replacement shape: the
destination size is supplied in characters, insufficient buffer is reported as a
failure, and a valid destination buffer is not overrun. Sandboxie keeps a local
helper instead of adding a new dependency, but the contract is the same:
bounded copy, null termination, and reject truncation at this wire boundary.

References:

- `https://learn.microsoft.com/en-us/cpp/c-runtime-library/reference/strcpy-wcscpy-mbscpy?view=msvc-170`
- `https://learn.microsoft.com/en-us/windows/win32/secbp/avoiding-buffer-overruns`
- `https://learn.microsoft.com/en-us/windows/win32/api/strsafe/nf-strsafe-stringcchcopyw`

## Schema

`QUEUE_NAME_WIRE_COPY_CONTRACT` says:

- `queueserver.h` owns the QueueServer declaration boundary for queue name
  normalization and lookup.
- `queuewire.h` fixes every queue name field at `QUEUE_NAME_MAXLEN` WCHARs.
- DLL-side queue helpers must validate and copy queue names through a bounded
  helper before sending a queue wire packet.
- Queue names that do not fit in `QUEUE_NAME_MAXLEN` including the terminating
  null are rejected with `STATUS_INVALID_PARAMETER`, not truncated into a
  different queue identity.
- Heap request packets must be checked after `Dll_Alloc` before writing header
  or queue-name fields.
- Server-side `MakeQueueName` still owns sandbox path prefixing and asterisk
  queue access policy; this SREV does not change queue access topology.

## Topology

```text
exported SbieDll queue helper
-> bounded queue-name wire copy
-> fixed QUEUE_*_REQ.queue_name field
-> PipeServer request
-> QueueServer::MakeQueueName
-> queue lookup / create / request / reply routing
```

## Logic Risk

The previous topology trusted caller queue names before the fixed wire shape
was enforced. That made the queue name field a stack/heap overwrite surface in
the DLL helper, and it could also silently corrupt neighboring request fields
such as event handles, request IDs, or payload metadata before the service saw
the packet.

## Fix

`callsvc.c` now owns `SbieDll_QueueCopyName`, a bounded queue-name copy helper
that writes at most `QUEUE_NAME_MAXLEN` WCHARs, always terminates the
destination, and returns failure when the source is NULL or does not fit.

All exported queue helpers now use this gate before calling `SbieDll_CallServer`
or creating proxy startup messages. Heap-backed queue request packets also check
the `Dll_Alloc` result before writing into the packet.

## Acceptance Gate

`docs/plan/check-srev-207.py` validates the draft-07 schema, official
references, `queueserver.h` owner declaration, fixed queue wire shape,
bounded-copy helper, removal of direct `wcscpy(...queue_name...)` writes from
the DLL queue helpers, allocation gates for heap-backed queue packets, split
ledger fragment, and unchanged server-side `MakeQueueName` / `FindQueueObj`
owner boundary. Runtime/build gate: Windows DLL/service build plus queue smoke
for normal `*USERPROXY`, `*GUIPROXY`, and `RPCSS_SXS` names, and malformed
overlong queue names returning `STATUS_INVALID_PARAMETER` without corrupting the
request packet.
