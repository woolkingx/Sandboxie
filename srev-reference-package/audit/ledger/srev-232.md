---
kind: srev-ledger-entry
id: SREV-232
title: Log Buffer Allocation Size Contract
status: patched-source-level-after-official-kernel-allocation-and-safe-integer-review-needs-windows-driver-runtime-proof
owner: Sandboxie/core/drv/log_buff.c
additional_owners:
  - Sandboxie/core/drv/log_buff.h
  - Sandboxie/core/drv/session.c
  - Sandboxie/core/drv/api.c
  - Sandboxie/install/SbieSettings.ini
spec: docs/plan/srev-232-log-buffer-allocation-size-contract.md
schema: docs/plan/srev-232-log-buffer-allocation-size-contract.schema.json
checker: docs/plan/check-srev-232.py
runtime_gate: Windows driver build plus monitor control smokes for default TraceBufferPages, explicit 2560 pages, zero pages, and excessive values.
---

### SREV-232: Log Buffer Allocation Size Contract

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official kernel allocation and safe-integer review; needs Windows driver runtime proof |
| Evidence | `Sandboxie/core/drv/log_buff.c` was the top unnamed reviewable core file after SREV-231. It owns the shared driver `LOG_BUFFER` ring allocation and byte-copy primitive used by `api.c` and `session.c`. Before this SREV, `log_buffer_init` passed `sizeof(LOG_BUFFER) + buffer_size` directly to `ExAllocatePoolWithTag` without proving that the flexible-tail allocation size fits in `SIZE_T`. `Api_Init` also trusted `log_buffer_init(8 * 8 * 1024)` without checking the returned pointer before later API log readers/writers used `Api_LogBuffer`. `Session_Api_MonitorControl` read `TraceBufferPages` as a page count, stored `pages * PAGE_SIZE` in an `ULONG`, and then passed `BuffSize * sizeof(WCHAR)` to `log_buffer_init`, even though `SbieSettings.ini` documents the setting as a count of 4K pages. |
| Data | `LOG_BUFFER`, `buffer_size`, `buffer_used`, `buffer_start_ptr`, `buffer_data[0]`, `log_buffer_init`, `ExAllocatePoolWithTag`, `Api_LogBuffer`, `Api_Init`, `Api_AddMessage`, `Api_GetMessage`, `TraceBufferPages`, `SESSION_MONITOR_BUF_SIZE`, `Session_Api_MonitorControl`, `session->monitor_log`, and `Conf_Get_Number`. |
| Schema | `LOG_BUFFER_ALLOCATION_SIZE_CONTRACT` says `log_buff.c` owns allocation of the flexible-tail `LOG_BUFFER` object; allocation byte count is `sizeof(LOG_BUFFER) + buffer_size`; that addition must be proven not to overflow `SIZE_T` before `ExAllocatePoolWithTag`; a zero byte ring has no legal entry capacity and must fail allocation; `TraceBufferPages` is a page count converted to bytes as `pages * PAGE_SIZE`; `Session_Api_MonitorControl` must not multiply the byte count by `sizeof(WCHAR)` before calling `log_buffer_init`; failed or invalid configured allocation falls back to `SESSION_MONITOR_BUF_SIZE`; and API log reader/writer paths must not dereference `Api_LogBuffer` when the global log buffer allocation failed. |
| Topology | API message log: `Api_Init -> log_buffer_init(8 * 8 * 1024) -> LOG_BUFFER`. Session monitor: `TraceBufferPages setting -> Conf_Get_Number -> pages * PAGE_SIZE bytes with overflow guard -> log_buffer_init(bytes) -> fallback SESSION_MONITOR_BUF_SIZE -> Session_MonitorPutEx / Session_Api_MonitorGetEx / Session_Api_MonitorGet2`. Shared ring protocol remains `[entry_size][seq][entry bytes][entry_size]`. |
| Logic Risk | Driver pool allocation size is a boundary. Once the flexible-tail buffer is allocated, later ring operations trust `buffer_size` and `buffer_data` to define the legal address range. An overflow in the allocation-size calculation can make the allocated object smaller than the stored `buffer_size`, turning later ring writes into pool memory corruption. The session monitor path also doubled the documented page-count capacity and could overflow the intermediate `ULONG` page-to-byte conversion before allocation. |
| Official Shape | `docs/plan/srev-232-log-buffer-allocation-size-contract.md` records Microsoft safe integer helper and system-space memory allocation references. |
| Fix | `log_buffer_init` now rejects zero-sized rings and any `buffer_size` whose flexible-tail allocation would overflow `SIZE_T`, computes `alloc_size`, and passes that named value to `ExAllocatePoolWithTag`. `Api_Init` now fails if the global API log ring cannot be allocated; `Api_AddMessage` returns when `Api_LogBuffer` is unavailable; and `Api_GetMessage` returns `STATUS_DEVICE_NOT_READY` before touching the ring. `Session_Api_MonitorControl` now reads `TraceBufferPages` into `BuffPages`, guards `pages * PAGE_SIZE` against the `log_buffer_init` header-addition limit, calls `log_buffer_init(BuffSize)`, and uses `SESSION_MONITOR_BUF_SIZE` as bytes for fallback. No ring entry layout, pop/read/write algorithm, monitor record format, `API_MONITOR_GET_EX`, `API_MONITOR_GET2`, API message log format, or lock topology changed. |
| Acceptance Gate | `docs/plan/check-srev-232.py` validates the draft-07 schema, official references, `log_buffer_init` zero/overflow gate before allocation, named `alloc_size`, global API log buffer allocation-failure gates, session `TraceBufferPages` page-count-to-byte conversion, removal of stale `* sizeof(WCHAR)` monitor allocation, fallback allocation, and split ledger fragment; `docs/plan/check-srev-232.sh` is the targeted wrapper. Runtime/build gate: Windows driver build plus monitor control smokes for default `TraceBufferPages`, explicit `TraceBufferPages=2560`, `TraceBufferPages=0`, and an excessive value. Valid values should allocate the documented page-count capacity; invalid/excessive values should fall back or fail without pool corruption. |
