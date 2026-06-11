# SREV-162: Driver Event Log Entry Size Gate

## Stage Gate

```text
stage: schema -> boundary -> topology -> logic -> action -> verify
input artifact: Sandboxie/core/drv/log.h, Sandboxie/core/drv/log.c, and Microsoft kernel error-log/string DDIs
output artifact: bounded driver event-log packet size and insertion-string length gate
owner: Sandboxie/core/drv/log.c
acceptance gate: docs/plan/check-srev-162.py and docs/plan/check-srev-162.sh
```

## Data

`log.h` is the driver logging API surface. `log.c` owns the local dispatch from
Sandboxie message codes to either Windows kernel error-log packets or the
Sandboxie popup/service log buffer. The event-log branch builds an
`IO_ERROR_LOG_PACKET`, appends up to two insertion strings after the packet
header, then calls `IoWriteErrorLogEntry`.

Before this SREV, `Log_Event_Msg` measured insertion strings with unbounded
`wcslen`, stored byte counts in `int`, accepted `entry_size <=
ERROR_LOG_MAXIMUM_SIZE`, and then cast `entry_size` to the `UCHAR` parameter
used by `IoAllocateErrorLogEntry`. The local code therefore did not encode the
documented DDI boundary: the packet size must be checked before the `UCHAR`
call boundary, and insertion strings must be proven null-terminated within the
packet budget before the driver copies them into the allocated packet.

## Official Shape

- Microsoft documents `IoAllocateErrorLogEntry` as taking `EntrySize` as
  `UCHAR`, warns that larger values are silently truncated, and says drivers
  should check that the value is less than `ERROR_LOG_MAXIMUM_SIZE` before
  calling it:
  `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-ioallocateerrorlogentry`.
- Microsoft documents `IO_ERROR_LOG_PACKET` as the header for an error-log
  entry and says null-terminated Unicode insertion strings follow the packet in
  memory:
  `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/ns-wdm-_io_error_log_packet`.
- Microsoft documents `IoWriteErrorLogEntry` as queuing a packet allocated with
  `IoAllocateErrorLogEntry` and freeing it after the write:
  `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-iowriteerrorlogentry`.
- Microsoft documents `RtlStringCbLengthW` as determining the byte length of a
  null-terminated string within a caller-supplied maximum byte count, excluding
  the terminating null from the returned length:
  `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntstrsafe/nf-ntstrsafe-rtlstringcblengtha`.

## Schema

`DRIVER_EVENT_LOG_ENTRY_SIZE_GATE` says:

- `log.c` owns the driver event-log packet construction path.
- `log.h` is the driver logging API surface, not the packet-size authority.
- `IoAllocateErrorLogEntry` is the kernel DDI boundary and accepts a `UCHAR`
  entry size.
- event-log `EntrySize` must be proven strictly less than
  `ERROR_LOG_MAXIMUM_SIZE` before casting to `UCHAR`.
- insertion strings must be null-terminated within the remaining packet budget
  before any copy into `IO_ERROR_LOG_PACKET` storage.
- `RtlStringCbLengthW` is the bounded local string-length gate for this path.
- oversize or unterminated insertion strings skip only the best-effort event-log
  record; they do not change Sandboxie policy, popup logging, service wakeup, or
  message IDs.
- Linux source gates are not Windows driver build/runtime proof.

## Topology

Legal event-log flow:

```text
Sandboxie driver message -> Log_Msg_Process
Log_Event_Msg -> bounded insertion-string byte counts
Log_Event_Msg -> EntrySize < ERROR_LOG_MAXIMUM_SIZE
IoAllocateErrorLogEntry(UCHAR EntrySize)
Log_Event_Msg -> copy exactly proven null-terminated insertion bytes
IoWriteErrorLogEntry
```

The event-log path is best-effort telemetry. It must not become the owner of
policy decisions, popup delivery, service wakeup, or message routing.

## Logic Risk

The old `<= ERROR_LOG_MAXIMUM_SIZE` check did not match the documented
precondition for the `UCHAR` DDI boundary. If the maximum is the first value
that cannot be represented without truncation, accepting equality can pass the
wrong size to `IoAllocateErrorLogEntry`. Separately, unbounded `wcslen` asks the
string to prove its terminator by scanning outside the packet budget. That is
the wrong proof direction for kernel telemetry: first prove the string fits
inside the legal packet shape, then copy it.

## Fix

`Log_Event_Msg` now computes packet and string byte counts as `SIZE_T`, reserves
only `ERROR_LOG_MAXIMUM_SIZE - 1` as the maximum legal packet size before the
`UCHAR` call boundary, and calls a local `Log_GetEventStringBytes` helper for
each insertion string. The helper uses `RtlStringCbLengthW` with the remaining
packet budget and returns false if the string is absent, too long, or not
null-terminated within that budget. The event packet is allocated only when
`entry_size < ERROR_LOG_MAXIMUM_SIZE`.

No popup log buffer path, `Api_AddMessage` wire shape, service wakeup,
message-id mapping, monitor logging, or policy decision changed.

## Verification

Source-level gates:

```bash
python3 docs/plan/check-srev-162.py
bash docs/plan/check-srev-162.sh
python3 docs/plan/check-core-coverage.py
```

Full closure matrix:

```bash
python3 docs/plan/check-srev-162.py &&
bash docs/plan/check-srev-162.sh &&
python3 docs/plan/check-core-coverage.py &&
for s in docs/plan/check-srev-0*.sh docs/plan/check-srev-1*.sh docs/plan/check-kpath-0*.sh; do bash "$s"; done &&
git diff --check
```

Runtime/build gate: Windows WDK driver build; event-log smoke for short
insertion strings, maximum-fitting insertion strings, over-budget insertion
strings, and normal popup-only messages proving the telemetry gate does not
change popup/service log delivery.
