# SREV-028: Monitor Get Uses Wrong Entry Payload Size

## Finding

`Session_MonitorPutEx` writes monitor entries as:

```text
[Time 8][Type 4][PID 4][TID 4][Data n]
```

The stored `entry_size` includes all 20 header bytes plus the data payload.
`Session_Api_MonitorGetEx` read the same four header fields, but computed the
returned data size as:

```c
entry_size - (4 + 4 + 4)
```

That subtracts only type, pid, and tid. The 8-byte timestamp remained counted as
string data, so `API_MONITOR_GET_EX` could copy 8 bytes beyond the real monitor
payload into the caller buffer and report a `UNICODE_STRING.Length` larger than
the actual data.

## Official API Shape

Primary Microsoft references:

- `https://learn.microsoft.com/en-us/windows/win32/api/subauth/ns-subauth-unicode_string`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-probeforread`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-probeforwrite`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/kernel/errors-in-referencing-user-space-addresses`

Relevant contract:

- `UNICODE_STRING.Length` is bytes and does not include a terminating NULL.
- `UNICODE_STRING.MaximumLength` is the total byte capacity of `Buffer`.
- A returned null-terminated string needs room for `Length + sizeof(WCHAR)`.
- User buffers and embedded user pointers must be probed and accessed under
  exception handling.

## Local Shape

Data:

- `log_buffer_push_entry` stores a size tag for the whole monitor payload.
- `Session_MonitorPutEx` writes timestamp, type, pid, tid, then monitor data.
- `Session_Api_MonitorGetEx` returns type/pid/tid separately and returns only
  data bytes through `UNICODE_STRING64`.

Schema:

- The monitor entry header is 20 bytes.
- The user-facing `UNICODE_STRING64.Length` must describe only the returned
  data bytes, not any header bytes.
- The returned string terminator must fit inside `MaximumLength`.

Topology:

```text
driver session monitor ring
  -> API_MONITOR_GET_EX
  -> user UNICODE_STRING64 { Length, MaximumLength, Buffer }
```

Logic:

- The ring entry is trusted local data, but the user output shape is constrained
  by `UNICODE_STRING64.MaximumLength`.
- Header size must be shared by writer and reader.
- Truncation must preserve a WCHAR terminator slot.

## Source Change

`SESSION_MONITOR_ENTRY_HEADER_SIZE` now names the shared 20-byte monitor header.
`Session_MonitorPutEx` uses it when computing entry size, and
`Session_Api_MonitorGetEx` subtracts it when deriving returned data size.

The read path now rejects impossible entries smaller than the header, leaves
space for a WCHAR terminator using `MaximumLength - sizeof(WCHAR)`, aligns the
truncated byte count to a WCHAR boundary, probes `data_size + sizeof(WCHAR)`,
and writes the terminator at `data_size / sizeof(WCHAR)`.

## Acceptance Gate

Source-level gate:

- Writer and reader both reference `SESSION_MONITOR_ENTRY_HEADER_SIZE`.
- No `entry_size - (4 + 4 + 4)` payload computation remains.
- No `MaximumLength - 1` byte terminator gate remains.
- The user probe covers `data_size + sizeof(WCHAR)`.

Windows runtime gate:

- Enable monitor logging and read `API_MONITOR_GET_EX` records through the DLL
  with a 256-WCHAR buffer.
- Verify returned `Length` excludes timestamp/type/pid/tid header bytes and the
  buffer is still NUL-terminated on exact-fit and truncated records.
