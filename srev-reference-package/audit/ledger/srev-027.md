---
kind: srev-ledger-entry
id: SREV-027
title: WFP Classify NetFwTrace Deferred Logger Path
status: patched-source-level-with-deferred-wfp-trace-logger-needs-windows-runtime-proof
owner: "Sandboxie/core/drv/wfp.c:914"
spec: docs/plan/srev-027-wfp-classify-logging-irql.md
schema: docs/plan/srev-027-wfp-classify-logging-irql.schema.json
checker: docs/plan/check-srev-027.sh
runtime_gate: NetFwTrace deferred logger passes Driver Verifier IRQL/DDI checking with IPv4/IPv6 TCP/UDP loopback/non-loopback blocked/permitted traffic, NetFwTrace on/off, process churn, rule refresh, monitor-log readback, queue overflow/drop observation, WFP unload drain, and negative controls proving no inline Session_MonitorPut/RtlStringCbPrintf path
---
### SREV-027: WFP Classify NetFwTrace Deferred Logger Path

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level with executable deferred logger path after official WFP IRQL review; needs Windows runtime proof |
| Evidence | `Sandboxie/core/drv/wfp.c:914` carried a TODO saying WFP classify is at `DISPATCH_LEVEL`, `Session_MonitorPut` uses pageable memory, and a logging proxy or nonpaged monitor path is needed. The commented block below it formatted strings and called `Session_MonitorPut`. |
| Data | WFP classify metadata, remote address/port/protocol fields, per-process `NetFwTrace` setting, and monitor log records. |
| Schema | WFP `classifyFn` may run at `IRQL <= DISPATCH_LEVEL`; `RtlStringCbPrintfA/W` require resident strings for arbitrary IRQL; `ExAcquireResourceExclusiveLite` is `<= APC_LEVEL`; PagedPool-backed monitor buffers are not DISPATCH-level data. Deferred logger design must separate DISPATCH-level nonpaged classify-side capture from PASSIVE-level monitor formatting and writeback. |
| Topology | WFP callout callback crosses into Sandboxie network policy and returns `FWPS_CLASSIFY_OUT`; `WFP_classify` now enqueues fixed nonpaged telemetry through `WFP_TraceEnqueueFromClassify`; `WFP_TraceThreadProc` drains the bounded queue and `WFP_TraceWrite` crosses into the session monitor subsystem outside classify. |
| Logic Risk | Re-enabling inline logging can turn a telemetry feature into a verifier bugcheck/IRQL crash path. The source-level deferred path removes the known wrong edge, but Windows Driver Verifier still has to prove the new queue, worker, unload, overflow, and monitor readback behavior. |
| Official Shape | `docs/plan/srev-027-wfp-classify-logging-irql.md` records Microsoft WFP classify IRQL, safe-string IRQL, spin-lock, ERESOURCE, pool, and data-logging contracts. |
| Required Strategy | Keep `WFP_classify` limited to block/permit decision plus fixed nonpaged capture. Keep string formatting and `Session_MonitorPut` in the deferred worker, then prove the path under Driver Verifier IRQL checking. |
| Deferred Logger Matrix | Source now has `WFP_TRACE_RECORD`, `WFP_TRACE_QUEUE_CAPACITY`, `WFP_TraceStart`, `WFP_TraceStop`, `WFP_TraceEnqueueFromClassify`, `WFP_TraceThreadProc`, and `WFP_TraceWrite`. Runtime proof must cover DISPATCH-safe classify-side capture of process id, direction, protocol, remote address/port, action, and trace bit into bounded nonpaged records; overflow/drop counter behavior; DISPATCH-safe producer synchronization; PASSIVE-level worker formatting; `Session_MonitorPut` only outside classify; process/sandbox/WFP/rule/monitor/driver-unload lifecycle; Driver Verifier IRQL/DDI; Special Pool; pool tracking; forced allocation failure; traffic stress; monitor readback; and negative controls proving no inline `Session_MonitorPut*`, `RtlStringCbPrintf*`, `session->monitor_log`, pageable allocation, or logging-disabled decision drift in `WFP_classify`. |
| Shared Runtime Capture Evidence | Runtime records use `docs/plan/srev-022-027-kernel-runtime-capture.schema.json` with feature path `wfp-deferred-logger`; `docs/plan/srev-022-027-kernel-runtime-capture-playbook.md` is the capture procedure; `docs/plan/check-srev-022-027-kernel-runtime-capture.sh` validates the shared kernel evidence contract. |
| Fix | The inactive unsafe logging implementation was removed from `WFP_classify`. `WFP_classify` now reads `wfp_proc->LogTraffic` while holding `WFP_MapLock`, releases that lock, then calls `WFP_TraceEnqueueFromClassify` with only fixed resident fields. The deferred trace subsystem owns a nonpaged bounded queue, drop counter, event, system-thread worker, PASSIVE-level string formatting, `Session_MonitorPut` writeback, and unload drain. No traffic block/permit behavior changed. |
| Acceptance Gate | `docs/plan/check-srev-027.sh` proves `WFP_classify` has no inline `Session_MonitorPut` or `RtlStringCbPrintf*` logging path, proves the source has `WFP_TRACE_RECORD`, bounded queue/drop counter, `WFP_TraceEnqueueFromClassify`, `WFP_TraceThreadProc`, `WFP_TraceWrite`, `WFP_TraceStart`, `WFP_TraceStop`, and proves the spec/ledger record the executable deferred logger path plus concrete executor/memory/lifecycle/verifier/negative-control matrix. Windows gate: NetFwTrace deferred logger passes Driver Verifier IRQL/DDI checking with IPv4/IPv6 TCP/UDP loopback/non-loopback blocked/permitted traffic, `NetFwTrace` on/off, process churn, rule refresh, monitor-log readback, overflow/drop observation, unload drain, and negative controls proving no inline `Session_MonitorPut` / `RtlStringCbPrintf` path. |
