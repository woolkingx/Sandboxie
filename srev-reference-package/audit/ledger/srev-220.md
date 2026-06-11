---
kind: srev-ledger-entry
id: SREV-220
title: Session MonitorGet2 Buffer Floor
status: patched-source-level-after-official-probeforwrite-and-local-log-buffer-wire-review-needs-windows-runtime-proof
owner: Sandboxie/core/drv/session.h
implementation: Sandboxie/core/drv/session.c
spec: docs/plan/srev-220-session-monitor-get2-buffer-floor.md
schema: docs/plan/srev-220-session-monitor-get2-buffer-floor.schema.json
checker: docs/plan/check-srev-220.py
runtime_gate: Windows driver build plus monitor bulk readback with buffer_len values 0, 1, sizeof(LOG_BUFFER_SIZE_T)-1, sizeof(LOG_BUFFER_SIZE_T), exact one-entry fit, and truncated multi-entry buffers. Short buffers must fail without writing past the user buffer, and valid buffers must remain zero-terminated.
---

### SREV-220: Session MonitorGet2 Buffer Floor

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official `ProbeForWrite` and local log-buffer wire review; needs Windows runtime proof |
| Evidence | `Sandboxie/core/drv/session.h` exports the session monitor surface, and `Sandboxie/core/drv/session.c` registers `API_MONITOR_GET2` to `Session_Api_MonitorGet2`. The bulk monitor output wire format is `([LOG_BUFFER_SIZE_T entry_size][entry bytes])... [LOG_BUFFER_SIZE_T 0]`. Before this fix, `Session_Api_MonitorGet2` probed the user output buffer for `buffer_len` bytes and later unconditionally wrote the terminating zero-sized entry. For `buffer_len < sizeof(LOG_BUFFER_SIZE_T)`, that terminator write crossed beyond the probed range; the loop guard also used `buffer_len - sizeof(LOG_BUFFER_SIZE_T)`, which underflowed for short buffers. |
| Data | `session.h`, `Session_Init`, `API_MONITOR_GET2`, `Session_Api_MonitorGet2`, `API_MONITOR_GET2_ARGS.buffer_ptr`, `API_MONITOR_GET2_ARGS.buffer_len`, `LOG_BUFFER_SIZE_T`, `log_buffer_get_size`, `log_buffer_get_bytes`, `log_buffer_pop_entry`, `Session_MonitorCount`, and `Session_MonitorPutEx`. |
| Schema | `SESSION_MONITOR_GET2_BUFFER_FLOOR` says `session.h` declares the session monitor API surface and `session.c` owns implementation/log state; `API_MONITOR_GET2` output is a sequence of size-prefixed entries terminated by one zero `LOG_BUFFER_SIZE_T`; the user output buffer must have at least `sizeof(LOG_BUFFER_SIZE_T)` bytes before the driver can write the terminator; `args->buffer_len` is an in/out user `ULONG*` cleared to zero before any data copy and later receives total bytes written on success or partial success; and the loop reserves one trailing `LOG_BUFFER_SIZE_T` slot before copying an entry. |
| Topology | `SbieAPI bulk trace caller -> API_MONITOR_GET2_ARGS { buffer_ptr, buffer_len* } -> driver Session_Api_MonitorGet2 -> ProbeForRead/ProbeForWrite(buffer_len*) -> require buffer_len >= sizeof(LOG_BUFFER_SIZE_T) -> ProbeForWrite(buffer_ptr, buffer_len) -> session monitor LOG_BUFFER -> copy zero or more [size][entry] blocks -> append [0] terminator -> write total used length through buffer_len*`. |
| Logic Risk | A tiny user buffer is still a valid pointer/range from the probe's perspective, but the protocol always writes a four-byte terminator. Probing one to three bytes does not make a four-byte write legal. The unsigned subtraction also made short buffers appear to have a huge remaining payload capacity. |
| Official Shape | `docs/plan/srev-220-session-monitor-get2-buffer-floor.md` records Microsoft `ProbeForWrite` as the official user-output-buffer validation reference. The LOG_BUFFER size-prefix/terminator shape is local schema. |
| Fix | `Session_Api_MonitorGet2` now rejects `buffer_len < sizeof(LOG_BUFFER_SIZE_T)` with `STATUS_BUFFER_TOO_SMALL` before probing or writing the output buffer. Because `*args->buffer_len.val` is already cleared to zero before this gate, callers do not receive a stale byte count on failure. No monitor record format, log-buffer storage, API number, `Session_MonitorPutEx` writer behavior, or successful bulk retrieval behavior changed. |
| Acceptance Gate | `docs/plan/check-srev-220.py` validates the draft-07 schema, official `ProbeForWrite` reference, `session.h` monitor declarations, `API_MONITOR_GET2` registration, `API_MONITOR_GET2_ARGS` shape, `LOG_BUFFER_SIZE_T` size-prefix schema, source-level minimum buffer gate before output-buffer probe, loop reservation of a trailing terminator slot, and split ledger fragment; `docs/plan/check-srev-220.sh` is the targeted wrapper. Runtime/build gate: Windows driver build plus monitor bulk readback with `buffer_len` values 0, 1, `sizeof(LOG_BUFFER_SIZE_T)-1`, `sizeof(LOG_BUFFER_SIZE_T)`, exact one-entry fit, and truncated multi-entry buffers. Short buffers must fail without writing past the user buffer, and valid buffers must remain zero-terminated. |
