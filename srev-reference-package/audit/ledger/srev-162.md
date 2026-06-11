---
kind: srev-ledger-entry
id: SREV-162
title: Driver Event Log Entry Size Gate
status: patched-source-needs-windows-runtime
owner: Sandboxie/core/drv/log.c
spec: docs/plan/srev-162-driver-event-log-entry-size-gate.md
schema: docs/plan/srev-162-driver-event-log-entry-size-gate.schema.json
checker: docs/plan/check-srev-162.py
runtime_gate: "Windows WDK driver build, event-log insertion-string smoke, over-budget insertion-string smoke, and popup/service log regression smoke"
---

### SREV-162: Driver Event Log Entry Size Gate

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after Microsoft kernel error-log DDI and ntstrsafe string-shape review; needs Windows driver build/runtime proof |
| Evidence | `Sandboxie/core/drv/log.h` was the top unnamed reviewable core file after SREV-161. `Sandboxie/core/drv/log.c` owns the event-log path. Before this SREV, `Log_Event_Msg` used unbounded `wcslen` to measure insertion strings, kept byte counts in `int`, accepted `entry_size <= ERROR_LOG_MAXIMUM_SIZE`, and then cast `entry_size` to the `UCHAR` `EntrySize` parameter for `IoAllocateErrorLogEntry`. |
| Data | `Sandboxie/core/drv/log.h`, `Sandboxie/core/drv/log.c`, `Log_Event_Msg`, `Log_Msg_Process`, `IO_ERROR_LOG_PACKET`, `IoAllocateErrorLogEntry`, `IoWriteErrorLogEntry`, `RtlStringCbLengthW`, `ERROR_LOG_MAXIMUM_SIZE`, `UCHAR EntrySize`, and driver-supplied null-terminated Unicode insertion strings. |
| Schema | `DRIVER_EVENT_LOG_ENTRY_SIZE_GATE` says `log.c` owns the driver event-log packet construction path; `IoAllocateErrorLogEntry` is the kernel DDI boundary and accepts a `UCHAR` entry size; event-log `EntrySize` must be proven strictly less than `ERROR_LOG_MAXIMUM_SIZE` before casting to `UCHAR`; insertion strings must be null-terminated within the remaining packet budget before any copy into `IO_ERROR_LOG_PACKET` storage; `RtlStringCbLengthW` is the bounded local string-length gate; oversize or unterminated insertion strings skip only the best-effort event-log record; and this SREV does not change Sandboxie policy, popup logging, service wakeup, message IDs, monitor logging, or `Api_AddMessage` wire shape. |
| Topology | Legal flow is Sandboxie driver message -> `Log_Msg_Process` -> `Log_Event_Msg` bounded insertion-string byte counts -> `EntrySize < ERROR_LOG_MAXIMUM_SIZE` -> `IoAllocateErrorLogEntry(UCHAR EntrySize)` -> copy exactly proven insertion-string bytes -> `IoWriteErrorLogEntry`. |
| Logic Risk | An inclusive maximum check at a `UCHAR` call boundary can pass a truncated packet size to the kernel DDI if the maximum is not representable as intended. Unbounded `wcslen` also scans for a terminator before proving the string is inside the packet budget, which reverses the safe kernel telemetry proof order. |
| Official Shape | `docs/plan/srev-162-driver-event-log-entry-size-gate.md` records Microsoft `IoAllocateErrorLogEntry`, `IO_ERROR_LOG_PACKET`, `IoWriteErrorLogEntry`, and `RtlStringCbLengthW` references. `docs/plan/srev-162-driver-event-log-entry-size-gate.schema.json` records the JSON Schema draft-07 local `DRIVER_EVENT_LOG_ENTRY_SIZE_GATE` contract. |
| Fix | `Log_Event_Msg` now uses `SIZE_T` packet and string byte counts, reserves only `ERROR_LOG_MAXIMUM_SIZE - 1` as the legal packet ceiling before the `UCHAR` DDI boundary, and calls `Log_GetEventStringBytes` for each insertion string. The helper uses `RtlStringCbLengthW` with the remaining packet budget and returns false for over-budget or unterminated strings. The packet is allocated only when `entry_size < ERROR_LOG_MAXIMUM_SIZE`. |
| Acceptance Gate | `docs/plan/check-srev-162.py` validates the draft-07 schema, official references, `log.h` API surface, local bounded string helper, strict event-log entry-size gate, removal of event-log `wcslen` length probes, ledger entry, and no change to popup/service log routing. `docs/plan/check-srev-162.sh` is the matrix wrapper. Runtime/build gate: Windows WDK driver build; event-log smoke for short insertion strings, maximum-fitting insertion strings, over-budget insertion strings, and popup/service log regression smoke. |
