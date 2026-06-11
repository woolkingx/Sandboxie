# SREV-227 Driver Registry Path Counted Copy

## Data

Owner files:

```text
Sandboxie/core/drv/mem.c
Sandboxie/core/drv/mem.h
Sandboxie/core/drv/driver.c
```

Reviewed nodes:

```text
DriverEntry
RegistryPath
UNICODE_STRING.Length
UNICODE_STRING.Buffer
Driver_RegistryPath
Mem_AllocStringEx
Mem_AllocUnicodeStringEx
```

## Schema

`DRIVER_REGISTRY_PATH_COUNTED_COPY` defines these local contracts:

- `DriverEntry` receives `RegistryPath` as a counted `UNICODE_STRING`.
- `driver.c` must save a copy of the registry path before `DriverEntry`
  returns.
- `Mem_AllocStringEx` remains the owner for NUL-terminated `WCHAR *` sources.
- `Mem_AllocUnicodeStringEx` owns conversion from a counted `UNICODE_STRING`
  into a local NUL-terminated pool string.
- The counted-copy helper must validate even byte length, non-null buffer for
  non-empty strings, and allocation-size overflow before copying.
- The counted-copy helper copies exactly `UNICODE_STRING.Length` bytes and
  synthesizes the local NUL terminator.
- This SREV does not change driver registry key semantics, pool ownership,
  startup ordering, public security initialization, home-path discovery, or
  `Mem_AllocStringEx` behavior for existing NUL-terminated callers.

## Topology

```text
I/O manager
  -> DriverEntry(DriverObject, PUNICODE_STRING RegistryPath)
  -> Mem_AllocUnicodeStringEx(Driver_Pool, RegistryPath, TRUE)
  -> Driver_RegistryPath local NUL-terminated copy
  -> later driver registry/open paths
```

The boundary is counted kernel input to a local NUL-terminated persistent
driver global. `RegistryPath->Buffer` alone is not the owner of string extent;
`RegistryPath->Length` is.

## Logic Risk

Before this SREV, `driver.c` saved `Driver_RegistryPath` by calling
`Mem_AllocStringEx(Driver_Pool, RegistryPath->Buffer, TRUE)`. That helper uses
`wcslen(model_string)` and therefore requires a NUL-terminated source. Microsoft
documents `DriverEntry` `RegistryPath` as a counted Unicode string and says the
driver should save a copy because the I/O manager frees the buffer after
`DriverEntry` returns. Microsoft `UNICODE_STRING` shape says `Length` is the
byte length and does not include a trailing NUL if one exists.

The minimal legal fix is to add a counted source helper and use it only at this
counted `RegistryPath` boundary.

## Official Shape

- https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nc-wdm-driver_initialize
- https://learn.microsoft.com/en-us/windows/win32/api/subauth/ns-subauth-unicode_string

## Fix

`mem.c` now exposes `Mem_AllocUnicodeStringEx`, which validates a counted
`UNICODE_STRING`, allocates `Length + sizeof(WCHAR)`, copies exactly `Length`
bytes, and writes the local terminator at `Length / sizeof(WCHAR)`.

`driver.c` now initializes `Driver_RegistryPath` from the counted helper instead
of treating `RegistryPath->Buffer` as a C string.

No other `Mem_AllocStringEx` caller or driver startup stage changed.

## Acceptance Gate

Source gate:

```bash
bash docs/plan/check-srev-227.sh
python3 docs/plan/check-core-coverage.py
git diff --check
```

Full historical matrix is deferred to the next batch checkpoint or shared
checker/ledger infrastructure change.

Runtime/build gate still required:

- Windows driver build for `mem.c`, `mem.h`, and `driver.c`.
- Driver load smoke proving a normal registry path still initializes
  `Driver_RegistryPath`.
- Fault-injected or harnessed counted `RegistryPath` without a trailing NUL
  proving the copy uses `Length`, not `wcslen`.
  malformed odd-length and null-buffer shapes should fail without scanning.
