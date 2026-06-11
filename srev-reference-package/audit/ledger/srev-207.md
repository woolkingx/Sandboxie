---
kind: srev-ledger-entry
id: SREV-207
title: Queue Name Wire Copy Contract
status: patched-source-level-after-official-bounded-string-copy-shape-review-needs-windows-runtime-proof
owner: Sandboxie/core/svc/queueserver.h
implementation: Sandboxie/core/dll/callsvc.c
wire_schema: Sandboxie/core/svc/queuewire.h
spec: docs/plan/srev-207-queue-name-wire-copy-contract.md
schema: docs/plan/srev-207-queue-name-wire-copy-contract.schema.json
checker: docs/plan/check-srev-207.py
runtime_gate: Windows DLL/service build plus queue smoke for normal *USERPROXY, *GUIPROXY, and RPCSS_SXS names, and malformed overlong queue names returning STATUS_INVALID_PARAMETER without corrupting the request packet
---

### SREV-207: Queue Name Wire Copy Contract

| Field | Content |
|---|---|
| Severity | [moderate] |
| Status | patched source-level after official bounded string copy shape review; needs Windows runtime proof |
| Evidence | `Sandboxie/core/svc/queueserver.h` was the top unnamed reviewable core file after SREV-206. It declares the `QueueServer` owner for fixed queue wire messages and the `MakeQueueName` / `FindQueueObj` name boundary. The server wire schema in `queuewire.h` fixes queue names at `QUEUE_NAME_MAXLEN` WCHARs. Before this fix, the exported DLL queue helpers in `Sandboxie/core/dll/callsvc.c` copied caller-supplied queue names into those fixed wire fields with `wcscpy`. A queue name with 64 or more WCHARs could overflow stack or heap request packets before the request reached `QueueServer::MakeQueueName`, so the server-side truncation guard was too late for the client wire boundary. |
| Data | `queueserver.h`, `QueueServer`, `MakeQueueName`, `FindQueueObj`, `queuewire.h`, `QUEUE_NAME_MAXLEN`, fixed `QUEUE_*_REQ.queue_name` fields, `SbieDll_QueueCreate`, `SbieDll_QueueGetReq`, `SbieDll_QueuePutRpl`, `SbieDll_QueuePutReqImpl`, `SbieDll_StartProxy`, `SbieDll_QueueGetRpl`, `SbieDll_QueueCopyName`, `Dll_Alloc`, and `STATUS_INVALID_PARAMETER`. |
| Schema | `QUEUE_NAME_WIRE_COPY_CONTRACT` says `queueserver.h` owns the QueueServer declaration boundary for queue name normalization and lookup; `queuewire.h` fixes every queue name field at `QUEUE_NAME_MAXLEN` WCHARs; DLL-side queue helpers must validate and copy queue names through a bounded helper before sending a queue wire packet; queue names that do not fit including the terminating null are rejected with `STATUS_INVALID_PARAMETER`; heap request packets must be checked after `Dll_Alloc` before writing header or queue-name fields; and server-side `MakeQueueName` still owns sandbox path prefixing and asterisk queue access policy. |
| Topology | Legal flow is `exported SbieDll queue helper -> bounded queue-name wire copy -> fixed QUEUE_*_REQ.queue_name field -> PipeServer request -> QueueServer::MakeQueueName -> queue lookup / create / request / reply routing`. |
| Logic Risk | The previous topology trusted caller queue names before the fixed wire shape was enforced. That made the queue name field a stack/heap overwrite surface in the DLL helper, and it could also silently corrupt neighboring request fields such as event handles, request IDs, or payload metadata before the service saw the packet. |
| Official Shape | `docs/plan/srev-207-queue-name-wire-copy-contract.md` records Microsoft `wcscpy`, buffer-overrun guidance, and `StringCchCopyW` bounded-copy references. `docs/plan/srev-207-queue-name-wire-copy-contract.schema.json` records the JSON Schema draft-07 local `QUEUE_NAME_WIRE_COPY_CONTRACT` contract. |
| Fix | `callsvc.c` now owns `SbieDll_QueueCopyName`, a bounded queue-name copy helper that writes at most `QUEUE_NAME_MAXLEN` WCHARs, always terminates the destination, and returns failure when the source is NULL or does not fit. All exported queue helpers now use this gate before calling `SbieDll_CallServer` or creating proxy startup messages. Heap-backed queue request packets also check the `Dll_Alloc` result before writing into the packet. |
| Acceptance Gate | `docs/plan/check-srev-207.py` validates the draft-07 schema, official references, `queueserver.h` owner declaration, fixed queue wire shape, bounded-copy helper, removal of direct `wcscpy(...queue_name...)` writes from the DLL queue helpers, allocation gates for heap-backed queue packets, split ledger fragment, and unchanged server-side `MakeQueueName` / `FindQueueObj` owner boundary; `docs/plan/check-srev-207.sh` is the targeted wrapper. Runtime/build gate: Windows DLL/service build plus queue smoke for normal `*USERPROXY`, `*GUIPROXY`, and `RPCSS_SXS` names, and malformed overlong queue names returning `STATUS_INVALID_PARAMETER` without corrupting the request packet. |
