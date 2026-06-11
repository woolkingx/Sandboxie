---
kind: srev-ledger-entry
id: SREV-028
title: Monitor Get Uses Wrong Entry Payload Size
status: patched-source-level-after-official-unicode-string-and-user-buffer-contract-anal
owner: "Sandboxie/core/drv/session.c:616-617"
spec: docs/plan/srev-028-monitor-get-entry-size.md
schema: docs/plan/srev-028-monitor-get-entry-size.schema.json
checker: docs/plan/check-srev-028.sh
runtime_gate: "monitor readback shows `Length` excludes header bytes and exact-fit/truncated outputs remain NUL-terminated"
---
### SREV-028: Monitor Get Uses Wrong Entry Payload Size

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official UNICODE_STRING and user-buffer contract analysis; needs Windows monitor runtime proof |
| Evidence | `Sandboxie/core/drv/session.c:616-617` writes monitor entries as `[Time 8][Type 4][PID 4][TID 4][Data n]`, but `session.c:1146` computed returned data with `entry_size - (4 + 4 + 4)` and `session.c:1147-1154` used `MaximumLength - 1` / `data_size + 1` for a WCHAR string terminator. |
| Data | Session monitor ring entries and the `API_MONITOR_GET_EX` `UNICODE_STRING64` output buffer. |
| Schema | Monitor entry header is 20 bytes. `UNICODE_STRING.Length` and `MaximumLength` are byte counts; `Length` excludes the terminating NULL; a returned WCHAR string needs `Length + sizeof(WCHAR)` capacity. |
| Topology | Driver monitor ring data crosses the driver API boundary into a user-provided embedded `UNICODE_STRING64.Buffer`. |
| Logic Risk | Reader over-counts monitor payload by 8 bytes, can copy bytes beyond the actual monitor record into the caller buffer, and can probe/write only one byte of terminator space for a WCHAR string. |
| Official Shape | `docs/plan/srev-028-monitor-get-entry-size.md` records Microsoft `UNICODE_STRING`, `ProbeForRead`, `ProbeForWrite`, and embedded user-pointer validation posture. |
| Fix | `SESSION_MONITOR_ENTRY_HEADER_SIZE` now names the shared 20-byte header. The writer uses it for entry size; the reader rejects entries smaller than the header, subtracts the full header, reserves `MaximumLength - sizeof(WCHAR)` terminator capacity, aligns truncation to a WCHAR boundary, probes `data_size + sizeof(WCHAR)`, and writes the terminator at the WCHAR index. |
| Acceptance Gate | `docs/plan/check-srev-028.sh` proves no old `entry_size - (4 + 4 + 4)` / `MaximumLength - 1` shape remains and writer/reader share `SESSION_MONITOR_ENTRY_HEADER_SIZE`. Windows gate: monitor readback shows `Length` excludes header bytes and exact-fit/truncated outputs remain NUL-terminated. |
