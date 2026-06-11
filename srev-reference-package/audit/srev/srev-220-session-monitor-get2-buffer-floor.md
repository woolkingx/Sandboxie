# SREV-220: Session MonitorGet2 Buffer Floor

## Stage

data -> schema -> boundary -> topology -> logic -> action -> verify

## Evidence

`Sandboxie/core/drv/session.h` was the top unnamed reviewable core file after
SREV-219. It exports the session monitor surface through
`Session_MonitorPut`, `Session_MonitorPutEx`, and the session initialization
that registers `API_MONITOR_GET2`.

`Sandboxie/core/drv/session.c` implements `Session_Api_MonitorGet2` as the bulk
monitor reader. The wire format written to the user buffer is:

```text
([LOG_BUFFER_SIZE_T entry_size][entry bytes])... [LOG_BUFFER_SIZE_T 0]
```

Before this fix, the function probed the user buffer for `buffer_len` bytes and
then unconditionally wrote the terminating zero-sized entry. When
`buffer_len < sizeof(LOG_BUFFER_SIZE_T)`, the probe could succeed for the small
range but the final `*(LOG_BUFFER_SIZE_T*)buffer_ptr = 0` write crossed beyond
the probed output range. The loop guard also used
`buffer_len - sizeof(LOG_BUFFER_SIZE_T)`, which underflowed for short buffers.

## Data

`session.h`, `Session_Init`, `API_MONITOR_GET2`, `Session_Api_MonitorGet2`,
`API_MONITOR_GET2_ARGS.buffer_ptr`, `API_MONITOR_GET2_ARGS.buffer_len`,
`LOG_BUFFER_SIZE_T`, `log_buffer_get_size`, `log_buffer_get_bytes`,
`log_buffer_pop_entry`, `Session_MonitorCount`, and `Session_MonitorPutEx`.

## Official Shape

Microsoft documents `ProbeForWrite` as validating write access to a user-mode
buffer by address, length, and alignment. It also states robust drivers must
still handle protection changes after probing. The local invariant is therefore
not only "probe something"; the bytes later written must fit inside the same
validated output range.

Reference:

- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-probeforwrite`

## Schema

`SESSION_MONITOR_GET2_BUFFER_FLOOR` says:

- `session.h` declares the session monitor API surface; `session.c` owns the
  implementation and monitor log state.
- `API_MONITOR_GET2` output is a sequence of size-prefixed entries terminated
  by one zero `LOG_BUFFER_SIZE_T`.
- The user output buffer must have at least `sizeof(LOG_BUFFER_SIZE_T)` bytes
  before the driver can write the terminator.
- `args->buffer_len` is an in/out user `ULONG*`; it is cleared to zero before
  any data copy and later receives the total bytes written on success or
  partial success.
- The loop must reserve one trailing `LOG_BUFFER_SIZE_T` slot before copying an
  entry.
- Linux source proof cannot replace Windows monitor runtime proof.

## Topology

```text
SbieAPI bulk trace caller
-> API_MONITOR_GET2_ARGS { buffer_ptr, buffer_len* }
-> driver Session_Api_MonitorGet2
-> ProbeForRead/ProbeForWrite(buffer_len*)
-> require buffer_len >= sizeof(LOG_BUFFER_SIZE_T)
-> ProbeForWrite(buffer_ptr, buffer_len)
-> session monitor LOG_BUFFER
-> copy zero or more [size][entry] blocks
-> append [0] terminator
-> write total used length through buffer_len*
```

## Logic Risk

The bulk reader had the right high-level protocol but was missing the minimum
output-size floor. A tiny user buffer is still a user buffer: probing one to
three bytes does not make a four-byte terminator write legal. The unsigned
subtraction in the loop guard also made short buffers appear to have a huge
remaining payload capacity.

## Fix

`Session_Api_MonitorGet2` now rejects `buffer_len < sizeof(LOG_BUFFER_SIZE_T)`
with `STATUS_BUFFER_TOO_SMALL` before probing or writing the output buffer.
Because `*args->buffer_len.val` is already cleared to zero before this gate,
callers do not receive a stale byte count on failure.

No monitor record format, log-buffer storage, API number, `Session_MonitorPutEx`
writer behavior, or successful bulk retrieval behavior changed.

## Acceptance Gate

`docs/plan/check-srev-220.py` validates the draft-07 schema, official
`ProbeForWrite` reference, `session.h` monitor declarations, `API_MONITOR_GET2`
registration, `API_MONITOR_GET2_ARGS` shape, `LOG_BUFFER_SIZE_T` size-prefix
schema, source-level minimum buffer gate before output-buffer probe, loop
reservation of a trailing terminator slot, and split ledger fragment.

Runtime/build gate: Windows driver build plus monitor bulk readback with
`buffer_len` values 0, 1, `sizeof(LOG_BUFFER_SIZE_T) - 1`,
`sizeof(LOG_BUFFER_SIZE_T)`, exact one-entry fit, and truncated multi-entry
buffers. Short buffers must fail without writing past the user buffer, and valid
buffers must remain zero-terminated.
