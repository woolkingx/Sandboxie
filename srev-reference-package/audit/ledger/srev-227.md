---
kind: srev-ledger-entry
id: SREV-227
title: Driver Registry Path Counted Copy
status: patched-source-level-after-official-driverentry-unicode-string-shape-review-needs-windows-driver-runtime-proof
owner: Sandboxie/core/drv/mem.c
spec: docs/plan/srev-227-driver-registry-path-counted-copy.md
schema: docs/plan/srev-227-driver-registry-path-counted-copy.schema.json
checker: docs/plan/check-srev-227.py
runtime_gate: "Windows driver build plus DriverEntry registry path counted-copy smokes"
---
### SREV-227: Driver Registry Path Counted Copy

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official `DriverEntry` / `UNICODE_STRING` shape review; needs Windows driver runtime proof |
| Evidence | `Sandboxie/core/drv/mem.c` was the top unnamed reviewable core file after SREV-226. It owns `Mem_AllocStringEx`, which copies NUL-terminated `WCHAR *` sources by calling `wcslen`; `Sandboxie/core/drv/mem.h` owns the memory helper declarations. `Sandboxie/core/drv/driver.c` used that helper as `Mem_AllocStringEx(Driver_Pool, RegistryPath->Buffer, TRUE)` to save `Driver_RegistryPath` from the `DriverEntry` `RegistryPath` parameter. Microsoft documents `DriverEntry` `RegistryPath` as a counted `UNICODE_STRING` and says the driver should save a copy before return because the I/O manager frees the buffer. |
| Data | `mem.c`, `mem.h`, `driver.c`, `DriverEntry`, `RegistryPath`, `UNICODE_STRING.Length`, `UNICODE_STRING.Buffer`, `Driver_RegistryPath`, `Mem_AllocStringEx`, and `Mem_AllocUnicodeStringEx`. |
| Schema | `DRIVER_REGISTRY_PATH_COUNTED_COPY` says `DriverEntry` receives `RegistryPath` as a counted `UNICODE_STRING`; `driver.c` must save a copy before `DriverEntry` returns; `Mem_AllocStringEx` remains the owner for NUL-terminated `WCHAR *` sources; `Mem_AllocUnicodeStringEx` owns conversion from counted `UNICODE_STRING` into local NUL-terminated pool string; the helper validates even byte length, non-null buffer for non-empty strings, and allocation-size overflow; then copies exactly `Length` bytes and synthesizes the local terminator. |
| Topology | I/O manager passes `PUNICODE_STRING RegistryPath` to `DriverEntry`; `driver.c` calls `Mem_AllocUnicodeStringEx(Driver_Pool, RegistryPath, TRUE)`; `mem.c` copies by counted byte length and publishes a local NUL-terminated `Driver_RegistryPath` for later registry paths. |
| Logic Risk | `RegistryPath->Buffer` alone is not a C-string extent. Calling `wcslen` on it can scan past the counted string if the I/O manager buffer lacks a trailing NUL, and it also ignores embedded NUL/count semantics. The legal boundary is counted kernel input to local persistent NUL-terminated driver state. |
| Official Shape | `docs/plan/srev-227-driver-registry-path-counted-copy.md` records Microsoft `DRIVER_INITIALIZE` / `DriverEntry` and `UNICODE_STRING` references. |
| Fix | `mem.h` and `mem.c` now provide `Mem_AllocUnicodeStringEx`, which validates counted shape, allocates `Length + sizeof(WCHAR)`, copies exactly `Length` bytes, and writes the terminator at `Length / sizeof(WCHAR)`. `driver.c` now uses this helper for `Driver_RegistryPath`. Existing `Mem_AllocStringEx` behavior for NUL-terminated callers is unchanged. |
| Acceptance Gate | `docs/plan/check-srev-227.py` validates the draft-07 schema, official references, helper declaration, counted-source gates, exact-length copy and synthesized terminator, replacement of the stale `RegistryPath->Buffer` C-string copy, and ledger entry; `docs/plan/check-srev-227.sh` is the targeted wrapper. Runtime/build gate: Windows driver build; normal driver load; counted RegistryPath without trailing NUL; odd-length/null-buffer malformed harness cases. |
