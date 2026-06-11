---
kind: srev-ledger-entry
id: SREV-191
title: Named Pipe Pending I/O Lifetime Contract
status: patched-source-level-after-official-ntreadfile-cancelio-and-event-shape-review-needs-windows-runtime-proof
owner: Sandboxie/core/svc/namedpipeserver.cpp
spec: docs/plan/srev-191-namedpipe-pending-io-lifetime-contract.md
schema: docs/plan/srev-191-namedpipe-pending-io-lifetime-contract.schema.json
checker: docs/plan/check-srev-191.py
runtime_gate: Windows SbieSvc build plus named-pipe read write concurrent same-handle timeout cancel and blocked-peer smoke proving no stale event wrong completion stack corruption nonzero timeout payload or service-wide deadlock
---
### SREV-191: Named Pipe Pending I/O Lifetime Contract

| Field | Content |
|---|---|
| Severity | [blocker] |
| Status | patched source-level after official `NtReadFile` / `NtWriteFile`, `IO_STATUS_BLOCK`, `CancelIo`, and event-shape review; needs Windows runtime proof |
| Evidence | `Sandboxie/core/svc/namedpipeserver.h` was the top unnamed reviewable core file after SREV-190, and the concrete owned implementation is `Sandboxie/core/svc/namedpipeserver.cpp`. `ReadHandler` and `WriteHandler` issued `NtReadFile` / `NtWriteFile` with a stack `IO_STATUS_BLOCK`, a service-owned request or reply buffer, and a per-proxy event. On timeout they called `CancelIo(ProxyPipe->hPipe)`, wrote local cancelled status, and returned without proving the pending operation had completed. `ProxyHandle::Find` also allows multiple service requests to hold the same proxy handle concurrently, while the proxy used one shared event. |
| Data | `PROXY_PIPE`, `hPipe`, `hEvent`, `pIoLock`, `NamedPipeServer::OpenHandler`, `CloseCallback`, `SetHandler`, `ReadHandler`, `WriteHandler`, `NtReadFile`, `NtWriteFile`, `NtSetInformationFile`, `CancelIo`, `WaitForSingleObject`, `ResetEvent`, `IO_STATUS_BLOCK`, `NAMED_PIPE_READ_RPL.data`, and `NAMED_PIPE_WRITE_REQ.data`. |
| Schema | `NAMEDPIPE_PENDING_IO_LIFETIME_CONTRACT` says SbieSvc owns every `IO_STATUS_BLOCK` and transfer buffer pointer passed to native named-pipe read/write until completion; `STATUS_PENDING` requires waiting for completion before trusting the final `IO_STATUS_BLOCK`; `CancelIo` requests cancellation but does not prove completion; timeout paths must wait for completion after requesting cancellation before returning `STATUS_CANCELLED` with zero transfer bytes; the reused event is reset before each issue; only one native operation may use one proxied named-pipe handle event at a time. |
| Topology | Legal flow is `proxy handle -> per-handle I/O lock -> ResetEvent -> NtReadFile/NtWriteFile -> STATUS_PENDING bounded wait -> timeout CancelIo request -> wait for completion event -> local STATUS_CANCELLED/zero transfer reply -> release lock -> reply`. LPC and ALPC proxy handles do not own this named-pipe I/O event/lock topology. |
| Logic Risk | `CancelIo` is not a completion barrier. Returning immediately after it can create use-after-return on the stack `IO_STATUS_BLOCK` and use-after-free or stale-copy behavior on service message buffers. Concurrent operations on the same proxy handle can also use the same event, making completion signals ambiguous. |
| Official Shape | `docs/plan/srev-191-namedpipe-pending-io-lifetime-contract.md` records Microsoft `NtReadFile`, `NtWriteFile`, `IO_STATUS_BLOCK`, `CancelIo`, `CancelIoEx`, `ReadFile`, `WriteFile`, `CreateEvent`, and `ResetEvent` references. `docs/plan/srev-191-namedpipe-pending-io-lifetime-contract.schema.json` records the JSON Schema draft-07 local `NAMEDPIPE_PENDING_IO_LIFETIME_CONTRACT` contract. |
| Fix | `PROXY_PIPE` now owns an optional per-handle `CRITICAL_SECTION` pointer. `OpenHandler` allocates and initializes it for named-pipe file handles before publishing the proxy handle, while `CloseCallback` deletes and frees it. `SetHandler`, `ReadHandler`, and `WriteHandler` serialize native named-pipe operations through that lock. `ReadHandler` and `WriteHandler` reset the event before issuing native I/O and, on pending timeout, request `CancelIo`, wait for the completion event as a lifetime barrier, and return local `STATUS_CANCELLED` with zero transfer bytes. |
| Acceptance Gate | `docs/plan/check-srev-191.py` validates the draft-07 schema, official references, `PROXY_PIPE` lock lifetime, `OpenHandler` publication, `CloseCallback` cleanup, `SetHandler` serialization, read/write event reset and completion-after-cancel ordering, stale immediate-return timeout removal, and the split ledger fragment; `docs/plan/check-srev-191.sh` is the matrix wrapper. Runtime gate: Windows SbieSvc build plus named-pipe read/write, concurrent same-handle requests, blocked-peer timeout/cancel, and service liveness smoke proving no stale event, wrong completion, stack corruption, nonzero timeout payload, or service-wide deadlock. |
