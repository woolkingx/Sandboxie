# SREV-232: Log Buffer Allocation Size Contract

## Stage

data -> schema -> boundary -> topology -> logic -> action -> verify

## Evidence

After SREV-231, `Sandboxie/core/drv/log_buff.c` was the top unnamed reviewable
core file. It owns the shared driver `LOG_BUFFER` ring allocation and byte-copy
primitive used by both the API popup/message log and the session monitor log.

Before this SREV, `log_buffer_init` allocated:

```c
ExAllocatePoolWithTag(PagedPool, sizeof(LOG_BUFFER) + buffer_size, tzuk)
```

without proving that `sizeof(LOG_BUFFER) + buffer_size` fits in `SIZE_T`.
`Api_Init` also trusted `log_buffer_init(8 * 8 * 1024)` without checking the
returned pointer before later API log readers/writers used `Api_LogBuffer`.
`Session_Api_MonitorControl` read `TraceBufferPages` as a page count, stored
`pages * PAGE_SIZE` in an `ULONG`, and then passed `BuffSize * sizeof(WCHAR)` to
`log_buffer_init`. The user-facing setting documents `TraceBufferPages` as a
count of 4K pages, so the legal allocation size is `pages * PAGE_SIZE` bytes,
not `pages * PAGE_SIZE * sizeof(WCHAR)`.

## Data

`LOG_BUFFER`, `buffer_size`, `buffer_used`, `buffer_start_ptr`,
`buffer_data[0]`, `log_buffer_init`, `ExAllocatePoolWithTag`,
`Api_LogBuffer`, `Api_Init`, `Api_AddMessage`, `Api_GetMessage`,
`TraceBufferPages`, `SESSION_MONITOR_BUF_SIZE`, `Session_Api_MonitorControl`,
`session->monitor_log`, and `Conf_Get_Number`.

## Official Shape

Microsoft documents kernel safe integer helpers such as `RtlULongMult` as
returning `STATUS_INTEGER_OVERFLOW` when a multiplication overflows the target
type. That is the official arithmetic posture for driver-size calculations.

Microsoft also documents system-space memory allocation as an explicit
`NumberOfBytes` request and says drivers should check a null return from
`ExAllocatePoolWithTag`.

References:

- https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntintsafe/nf-ntintsafe-rtlulongmult
- https://learn.microsoft.com/en-us/windows-hardware/drivers/kernel/allocating-system-space-memory

## Schema

`LOG_BUFFER_ALLOCATION_SIZE_CONTRACT` says:

- `log_buff.c` owns allocation of the flexible-tail `LOG_BUFFER` object.
- The allocation byte count is `sizeof(LOG_BUFFER) + buffer_size`.
- That addition must be proven not to overflow `SIZE_T` before
  `ExAllocatePoolWithTag`.
- A zero byte ring has no legal entry capacity and must fail allocation.
- `TraceBufferPages` is a page count; session monitor allocation converts it to
  bytes as `pages * PAGE_SIZE`.
- `Session_Api_MonitorControl` must not multiply the byte count by
  `sizeof(WCHAR)` before calling `log_buffer_init`.
- Failed or invalid configured allocation falls back to
  `SESSION_MONITOR_BUF_SIZE`.
- API log reader/writer paths must not dereference `Api_LogBuffer` when the
  global log buffer allocation failed.

## Topology

```text
API message log
-> Api_Init
-> log_buffer_init(8 * 8 * 1024)
-> LOG_BUFFER

Session monitor
-> TraceBufferPages setting
-> Conf_Get_Number
-> pages * PAGE_SIZE bytes with overflow guard
-> log_buffer_init(bytes)
-> fallback SESSION_MONITOR_BUF_SIZE
-> Session_MonitorPutEx / Session_Api_MonitorGetEx / Session_Api_MonitorGet2
```

The shared ring protocol remains:

```text
[entry_size][seq][entry bytes][entry_size]
```

This SREV changes only allocation-size legality, not entry format, sequence
lookup, pop behavior, monitor entry contents, or API message filtering.

## Logic Risk

Driver pool allocation size is a boundary: once the flexible-tail buffer is
allocated, every ring operation trusts `buffer_size` and `buffer_data` to define
the legal address range. An overflow in the allocation-size calculation can make
the allocated object smaller than the stored `buffer_size`, turning later ring
writes into pool memory corruption.

The session monitor path also had a semantic mismatch with the documented
setting: a page count was converted to bytes, then doubled as if it were a
WCHAR count. That wastes paged pool and hides the true capacity requested by
configuration.

## Fix

`log_buffer_init` now rejects zero-sized rings and rejects any `buffer_size`
whose flexible-tail allocation would overflow `SIZE_T`. It computes the
allocation in a named `alloc_size` variable before calling
`ExAllocatePoolWithTag`.

`Api_Init` now fails if the global API log ring cannot be allocated.
`Api_AddMessage` returns when `Api_LogBuffer` is unavailable, and
`Api_GetMessage` returns `STATUS_DEVICE_NOT_READY` before touching the ring.

`Session_Api_MonitorControl` now reads `TraceBufferPages` into `BuffPages`,
guards the `pages * PAGE_SIZE` conversion against the `log_buffer_init` header
addition limit, and calls `log_buffer_init(BuffSize)` directly. The fallback now
uses `SESSION_MONITOR_BUF_SIZE` as bytes.

No ring entry layout, pop/read/write algorithm, monitor record format,
`API_MONITOR_GET_EX`, `API_MONITOR_GET2`, API message log format, or lock
topology changed.

## Acceptance Gate

`docs/plan/check-srev-232.py` validates the draft-07 schema, official
references, `log_buffer_init` zero/overflow gate before allocation, named
`alloc_size`, global API log buffer allocation-failure gates, session
`TraceBufferPages` page-count-to-byte conversion, removal of stale
`* sizeof(WCHAR)` monitor allocation, fallback allocation, and split ledger
fragment.

Runtime/build gate: Windows driver build plus monitor control smokes for
default `TraceBufferPages`, explicit `TraceBufferPages=2560`, `TraceBufferPages=0`,
and an excessive value. Valid values should allocate the documented page-count
capacity; invalid/excessive values should fall back or fail without pool
corruption.
