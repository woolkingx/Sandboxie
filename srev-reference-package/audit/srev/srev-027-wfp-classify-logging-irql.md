# SREV-027: WFP Classify Logging IRQL Contract

## Finding

`Sandboxie/core/drv/wfp.c` had a large commented `NetFwTrace` logging block
inside `WFP_classify`. The comment already said the code runs at
`DISPATCH_LEVEL`, that `Session_MonitorPut` uses pageable memory, and that
`RtlStringCbPrintfW` / `RtlStringCbPrintfA` are not safe for this path.

The block was inactive, so the immediate behavior was a telemetry gap rather
than a live crash. The risk was that the commented implementation looked close
enough to be re-enabled later, even though the owner boundaries do not allow it.

## Official API Shape

Primary Microsoft references:

- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/fwpsk/nc-fwpsk-fwps_callout_classify_fn0`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntstrsafe/nf-ntstrsafe-rtlstringcbprintfa`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-keacquirespinlockraisetodpc`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-keinitializeevent`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-kesetevent`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-kewaitforsingleobject`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-pscreatesystemthread`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/nf-ntifs-zwwaitforsingleobject`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-exacquireresourceexclusivelite`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-exallocatepool2`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/network/data-logging`

Relevant contract:

- WFP `classifyFn` may be called at `IRQL <= DISPATCH_LEVEL`.
- `RtlStringCbPrintfA/W` may run at any IRQL only when all manipulated strings
  are always resident; otherwise the caller must be at `PASSIVE_LEVEL`.
- `KeAcquireSpinLockRaiseToDpc` raises the caller to the spin-lock/DPC path.
- `ExAcquireResourceExclusiveLite` requires `IRQL <= APC_LEVEL`.
- Paged pool memory cannot be accessed from code that runs at `DISPATCH_LEVEL`;
  a DISPATCH-level path must use nonpaged memory for data it touches there.
- `KeInitializeEvent` requires caller-supplied event storage to be resident.
- `KeSetEvent(..., Wait = FALSE)` is the legal wake shape for the classify
  producer path; it does not immediately chain into a wait.
- `KeWaitForSingleObject` with `Timeout = NULL` belongs to the worker/passive
  wait path, not the classify callback.
- `PsCreateSystemThread` is a `PASSIVE_LEVEL` creation path; the created system
  thread runs in kernel mode and must terminate itself with
  `PsTerminateSystemThread`.
- `ZwWaitForSingleObject` for the thread handle is an unload/rollback wait and
  must remain on the PASSIVE-level load/unload side, never in classify.
- WFP data logging examples keep classify-side work simple; heavier logging
  should preserve the classify IRQL contract rather than blocking on pageable
  resources.

## Local Shape

Data:

- WFP fixed values and metadata carry process id, remote address, remote port,
  protocol, and action rights.
- `WFP_PROCESS.LogTraffic` records the `NetFwTrace` setting.
- `Session_MonitorPutEx` writes monitor records into `session->monitor_log`.

Schema:

- `WFP_classify` is a WFP callout callback and must be safe at
  `DISPATCH_LEVEL`.
- `Session_MonitorPutEx` calls `Session_Get`, which raises to `APC_LEVEL` and
  acquires `Session_ListLock` with `ExAcquireResourceExclusiveLite`.
- `log_buffer_init` allocates `LOG_BUFFER` from `PagedPool`.

Topology:

```text
WFP classify callback
  -> WFP process policy map under WFP_MapLock
  -> action decision on FWPS_CLASSIFY_OUT
  -x-> inline monitor logging
```

The forbidden edge is:

```text
DISPATCH-level WFP classify
  -> Session_MonitorPutEx
  -> ERESOURCE + PagedPool monitor buffer
```

Logic:

- Blocking/permitting traffic remains legal in `WFP_classify`.
- NetFwTrace logging now uses a different executor: `WFP_classify` enqueues a
  fixed nonpaged record, and `WFP_TraceThreadProc` later formats and writes the
  monitor record at `PASSIVE_LEVEL`.
- Inline string formatting plus `Session_MonitorPut` is not the correct fix.

## Source Change

The inactive inline logging implementation was removed from `WFP_classify`.
`WFP_classify` now records the per-process `NetFwTrace` bit while it owns the
WFP process map, then calls `WFP_TraceEnqueueFromClassify` after releasing
`WFP_MapLock`.

`WFP_TraceEnqueueFromClassify` copies only resident fixed facts into a bounded
nonpaged ring: process id, direction, IPv4/IPv6 shape, protocol, remote address,
remote port, and block/permit action. It uses `WFP_TraceLock` as the
DISPATCH-safe producer lock and increments `WFP_TraceDropCount` when the ring is
full.

`WFP_TraceThreadProc` is created by `WFP_TraceStart`, waits on
`WFP_TraceEvent`, drains queued records, and calls `WFP_TraceWrite`.
`WFP_TraceWrite` formats the monitor string and calls `Session_MonitorPut`
outside the classify callback. `WFP_TraceStop` stops the thread, waits for the
kernel thread handle, and frees the nonpaged ring during WFP unload and failed
load rollback.

No block/permit decision behavior changes in this patch.

## Runtime Verification Matrix

The source now has an executable deferred logger path, but it is not runtime
proven by Linux/source readback alone. The Windows gate must cover the executor,
stress source, and observable evidence:

| Axis | Required coverage |
|---|---|
| Verifier | Driver Verifier with IRQL checking / DDI compliance enabled for the Sandboxie driver |
| Traffic | sustained outbound TCP, inbound TCP when applicable, UDP, loopback, IPv4, IPv6, blocked traffic, and permitted traffic |
| Sandbox settings | `NetFwTrace=y`, normal no-trace path, `BlockInternet`, `BlockLoopback`, and rule-based block/permit |
| Logger shape | nonpaged classify-side capture plus deferred PASSIVE_LEVEL monitor write, or a fully DISPATCH-safe monitor writer |
| Evidence | no bugcheck, no verifier violation, no monitor-log corruption, no dropped block/permit decision, and monitor records contain process id, remote address, remote port, protocol, and action |
| Negative control | direct `Session_MonitorPut*` or `RtlStringCbPrintf*` from `WFP_classify` remains absent |
| Load | repeated high-rate traffic while starting/stopping sandboxed processes and refreshing rules |
| Regression | traffic behavior is unchanged when logging is disabled |

## Deferred Logger Matrix

The correct shape is not "make the old logging block compile". The classify path
captures only resident data that is legal at `DISPATCH_LEVEL`; the later
executor performs formatting and monitor ring writes at a legal IRQL.

Required dimensions:

- Classify-side data: process id, direction, layer id, protocol, remote
  address, remote port, action, `NetFwTrace` enabled bit, rule match result,
  and timestamp source.
- Memory owner: nonpaged fixed-size record, bounded queue/ring capacity,
  allocation-failure policy, overflow/drop counter, and pool tag.
- Synchronization owner: DISPATCH-safe producer lock or lock-free queue, no
  ERESOURCE, no pageable buffer, no blocking wait, and no pageable function in
  `WFP_classify`.
- Deferred executor: work item, system thread, or other PASSIVE_LEVEL owner
  that formats strings and calls `Session_MonitorPutEx`.
- Monitor record: process id, remote address, remote port, protocol, direction,
  block/permit action, rule id or no-rule marker, and drop/overflow diagnostic.
- Lifecycle: process exit, sandbox stop, WFP unload, rule refresh, monitor
  consumer attach/detach, and driver unload drain/cancel behavior.
- Verifier proof: Driver Verifier IRQL checking, DDI compliance checking,
  Special Pool for the logger tag, pool tracking, and forced allocation failure.

Negative controls:

- direct `Session_MonitorPut*` from `WFP_classify`;
- direct `RtlStringCbPrintf*` from `WFP_classify`;
- touching `session->monitor_log` from `WFP_classify`;
- pageable allocation or PagedPool-backed record touched at `DISPATCH_LEVEL`;
- queue overflow under high-rate traffic;
- logging disabled path changing block/permit decisions.

## Acceptance Gate

Source-level gate:

- `WFP_classify` must not call `Session_MonitorPut` / `Session_MonitorPutEx`.
- `WFP_classify` must not call `RtlStringCbPrintfA` / `RtlStringCbPrintfW`.
- `WFP_classify` must enqueue through `WFP_TraceEnqueueFromClassify` after
  releasing `WFP_MapLock`.
- `WFP_TraceEnqueueFromClassify` must write only fixed records into a bounded
  nonpaged queue/ring with a drop counter.
- `WFP_TraceThreadProc` / `WFP_TraceWrite` must be the only WFP NetFwTrace path
  that formats strings and calls `Session_MonitorPut`.
- The schema/spec/ledger must keep the deferred logger executor, memory owner,
  lifecycle, verifier, and negative-control matrix visible.
- The ledger must record the source-level deferred logger path and remaining
  Windows runtime gate.

Windows runtime gate:

- Run the matrix above on Windows.
- Confirm no bugcheck, no verifier violation, no monitor-log corruption, and no
  missed block/permit decisions while traffic logging is active.

## Shared Runtime Capture Evidence

This SREV shares a kernel runtime evidence contract with SREV-022:

```text
docs/plan/srev-022-027-kernel-runtime-capture-playbook.md
docs/plan/srev-022-027-kernel-runtime-capture.schema.json
docs/plan/check-srev-022-027-kernel-runtime-capture.sh
```

The machine feature path for this entry is `wfp-deferred-logger`.

Windows gate: validate captured WFP logger records against
`docs/plan/srev-022-027-kernel-runtime-capture.schema.json` before any
NetFwTrace logger behavior change.
