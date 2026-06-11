# SREV-194: Protected Root API String Contract

## Scope

Entry declaration surface:

```text
Sandboxie/core/drv/file.h
```

Implementation owner:

```text
Sandboxie/core/drv/file_flt.c
```

Producer:

```text
Sandboxie/core/svc/MountManager.cpp
Sandboxie/core/svc/MountManagerWire.h
```

This entry covers `API_PROTECT_ROOT` and `API_UNPROTECT_ROOT`, the driver API
functions declared in `file.h` and implemented by the filesystem minifilter.

## Official Shape

Microsoft documents `ProbeForRead` as validating that a user-mode buffer is in
the user portion of the address space and aligned. It raises exceptions on bad
ranges and must be called inside `try/except`; subsequent accesses to user-mode
buffers also need exception protection.

Microsoft documents bounded string length functions as intended for incoming
untrusted data in a buffer of known size: they calculate length without walking
past the end of the buffer and report the maximum when no terminator exists.

References:

- https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-probeforread
- https://learn.microsoft.com/en-us/cpp/c-runtime-library/reference/strnlen-strnlen-s?view=msvc-170

## Local Data

`SbieSvc` calls:

```text
SbieApi_Call(API_PROTECT_ROOT, 3, req->reg_root, TargetNtPath.c_str(), admin_only)
SbieApi_Call(API_UNPROTECT_ROOT, 1, req->reg_root)
```

`MountManager` validates `req->reg_root` as a fixed `MAX_REG_ROOT_LEN` string
and validates mount `file_root` inside the service request. After the driver API
crossing, however, the driver receives raw user-mode pointers in `parms[]`.

## Topology

Legal flow:

```text
MountManager request
-> service-side fixed/request-tail terminator validation
-> SbieApi_Call raw pointer arguments
-> Api_FastIo_DEVICE_CONTROL captures ULONG64 pointer values
-> File_Api_ProtectRoot/File_Api_UnprotectRoot bounded terminator gate
-> ProbeForRead exact bounded string bytes
-> PROTECTED_ROOT copy
-> File_ProtectedRoots list
```

The service-side check is compatibility evidence, not the driver owner gate.
The driver must still prove the pointer shape it reads.

## Risk

Before this fix, `File_Api_ProtectRoot` used `wcslen(file_root)` and then
`wcslen(reg_root)` on raw API pointer arguments. `File_Api_UnprotectRoot` used
`wcslen((WCHAR *)parms[1])` and copied the result into a fixed
`reg_root[MAX_REG_ROOT_LEN]` stack buffer. A malformed service-side caller,
stale pointer, unterminated fixed string, or oversized registry root could make
the driver scan past the legal input shape or copy past the fixed registry-root
buffer. `File_Api_ProtectRoot` also returned success if `Mem_Alloc` failed,
which could make the service believe protection was installed when it was not.

## Fix

- Add `File_ProtectedRootStringLen` as the local bounded terminator gate.
- Require `reg_root` to terminate within `MAX_REG_ROOT_LEN`.
- Require `file_root` to terminate within a bounded 32767-WCHAR driver cap and
  be non-empty.
- Probe exactly the captured bounded string bytes before copying.
- Remove unbounded `wcslen` from the protect/unprotect API handlers.
- Return `STATUS_INSUFFICIENT_RESOURCES` if protected-root allocation fails.

## Acceptance Gate

Source-level gate:

```bash
python3 docs/plan/check-srev-194.py
bash docs/plan/check-srev-194.sh
python3 docs/plan/check-core-coverage.py
```

Runtime gate:

```text
Windows driver build plus mount/unmount protected-root smoke with valid roots,
unterminated reg_root, oversized reg_root, empty file_root, malformed file_root
pointer, and allocation-failure fault injection if available.
```
