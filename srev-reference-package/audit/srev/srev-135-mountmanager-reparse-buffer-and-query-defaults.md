# SREV-135: MountManager Reparse Buffer And Query Defaults

## Stage Gate

| Field | Value |
|---|---|
| Stage | action |
| Input artifact | `Sandboxie/core/svc/MountManagerHelpers.cpp`, `Sandboxie/common/win32_ntddk.h`, Microsoft heap, `DeviceIoControl`, `FSCTL_GET_REPARSE_POINT`, and `REPARSE_DATA_BUFFER` references |
| Output artifact | `docs/plan/srev-135-mountmanager-reparse-buffer-and-query-defaults.schema.json`, `docs/plan/check-srev-135.py`, `docs/plan/check-srev-135.sh`, ledger row |
| Owner | `ImDiskOpenDeviceByMountPoint` and `ImDiskQueryDeviceSize` |
| Acceptance gate | source checker plus full SREV/KPATH/core coverage matrix; Windows service/runtime remains required |

## Evidence

`Sandboxie/core/svc/MountManagerHelpers.cpp` was the highest-ranked unnamed reviewable core file after SREV-134. `ImDiskOpenDeviceByMountPoint` opens a mount-point directory with `FILE_FLAG_OPEN_REPARSE_POINT`, asks `FSCTL_GET_REPARSE_POINT` for its reparse payload, interprets the result as `REPARSE_DATA_BUFFER.MountPointReparseBuffer`, trims one trailing slash from the substitute name, and opens the resulting NT device path through `ImDiskOpenDeviceByName`.

Before this SREV, the helper allocated its output buffer with `HEAP_GENERATE_EXCEPTIONS`, so allocation failure could raise through the service helper instead of returning the same `INVALID_HANDLE_VALUE` error shape as the rest of the function. It also trusted the returned reparse buffer after checking only `ReparseTag`; a malformed or truncated mount-point payload could make `SubstituteNameOffset` / `SubstituteNameLength` point outside the bytes returned by `DeviceIoControl`, or make the trailing-slash trim index underflow on a zero-length substitute name. In the same file, `ImDiskQueryDeviceSize` returned an uninitialized `ULONGLONG` when the device open, IOCTL, or proxy-type check failed.

Microsoft documents `HeapAlloc` with `HEAP_GENERATE_EXCEPTIONS` as raising an exception on failure instead of returning `NULL`, and documents `HeapAlloc` without that flag as returning `NULL` on failure. Microsoft documents `FSCTL_GET_REPARSE_POINT` as returning caller-allocated `REPARSE_DATA_BUFFER` data and returning the actual byte count through the length-returned path. Microsoft documents `DeviceIoControl` as reporting the size of data stored in the output buffer through `lpBytesReturned`. Microsoft documents `REPARSE_DATA_BUFFER` mount-point substitute-name offsets and lengths as byte counts into `PathBuffer`, with offsets divided by `sizeof(WCHAR)` to become array indexes.

Official references:

- https://learn.microsoft.com/en-us/windows/win32/api/heapapi/nf-heapapi-heapalloc
- https://learn.microsoft.com/en-us/windows-hardware/drivers/ifs/fsctl-get-reparse-point
- https://learn.microsoft.com/en-us/windows/win32/api/ioapiset/nf-ioapiset-deviceiocontrol
- https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/ns-ntifs-_reparse_data_buffer

## Data

`ImDiskOpenDeviceByMountPoint`, `MountPoint`, `AccessMode`, `hDir`, `ReparseData`, `DeviceIoControl`, `FSCTL_GET_REPARSE_POINT`, `dw`, `REPARSE_DATA_BUFFER`, `ReparseTag`, `ReparseDataLength`, `MountPointReparseBuffer`, `SubstituteNameOffset`, `SubstituteNameLength`, `PathBuffer`, `DeviceName`, `ImDiskOpenDeviceByName`, `HeapAlloc`, `HeapFree`, `CloseHandle`, `ImDiskQueryDeviceSize`, `IOCTL_IMDISK_QUERY_DEVICE`, `IMDISK_TYPE_PROXY`, and returned `ULONGLONG size`.

## Schema

`MOUNTMANAGER_REPARSE_BUFFER_AND_QUERY_DEFAULTS` says:

- `ImDiskOpenDeviceByMountPoint` treats `FSCTL_GET_REPARSE_POINT` output as untrusted counted data.
- `HeapAlloc` failure returns `INVALID_HANDLE_VALUE` without raising `HEAP_GENERATE_EXCEPTIONS` through the service helper.
- `ReparseDataLength` is bounded by the bytes `DeviceIoControl` reports before `MountPointReparseBuffer` fields are trusted.
- `MountPointReparseBuffer` substitute-name offset and length are `WCHAR`-aligned.
- Substitute-name offset plus length stays inside the returned `PathBuffer` bytes.
- Zero-length substitute names are rejected before trailing-slash trimming indexes the buffer.
- Non-mount-point reparse tags still fail before opening an ImDisk device name.
- Valid mount-point substitute names still flow to `ImDiskOpenDeviceByName` with existing trailing-slash trimming.
- `ImDiskQueryDeviceSize` returns zero when the device cannot be opened or queried as an ImDisk proxy device.

## Topology

The legal mount-point helper flow is:

```text
mount-point path
  -> CreateFile(... FILE_FLAG_OPEN_REPARSE_POINT ...)
  -> HeapAlloc(... HEAP_ZERO_MEMORY ...)
  -> DeviceIoControl(... FSCTL_GET_REPARSE_POINT ..., &dw)
  -> require IO_REPARSE_TAG_MOUNT_POINT
  -> require fixed mount-point header inside dw
  -> require ReparseDataLength inside dw
  -> require nonzero WCHAR-aligned SubstituteNameOffset/SubstituteNameLength inside PathBuffer bytes
  -> build counted UNICODE_STRING DeviceName
  -> optional trailing slash trim
  -> ImDiskOpenDeviceByName
  -> HeapFree
```

The legal query-size flow is:

```text
size = 0
  -> optional ImDiskOpenDeviceByName
  -> optional IOCTL_IMDISK_QUERY_DEVICE
  -> assign size only for IMDISK_TYPE_PROXY
  -> return size
```

## Logic Risk

The reparse payload crosses from filesystem-controlled bytes into a service-side device open. `ReparseTag` only says which union arm is intended; it does not prove that the returned byte count contains the mount-point fixed fields or that the counted substitute-name range is inside `PathBuffer`. Because the old trailing-slash trim indexed `DeviceName.Buffer[(DeviceName.Length >> 1) - 1]`, a zero-length substitute name could underflow before the helper ever reached `ImDiskOpenDeviceByName`.

The owner-local repair is to validate the counted payload shape before creating the `UNICODE_STRING`, not to change mount-point policy or the ImDisk device-open path. `ImDiskQueryDeviceSize` gets a separate local default-state fix because its return value has no legal data owner on failure unless it is initialized.

## Fix

`ImDiskOpenDeviceByMountPoint` now allocates the reparse buffer without `HEAP_GENERATE_EXCEPTIONS`, checks the allocation result, validates returned size, `ReparseDataLength`, substitute-name alignment, substitute-name nonzero length, and substitute-name range before building `DeviceName`, and guards trailing-slash trimming with `DeviceName.Length`. Invalid mount-point payloads return `ERROR_INVALID_DATA`; allocation failure returns `ERROR_NOT_ENOUGH_MEMORY`. Existing direct drive-letter and direct device-name paths are unchanged.

`ImDiskQueryDeviceSize` now initializes `size` to zero before any open or IOCTL edge.

## Acceptance Gate

`docs/plan/check-srev-135.py` validates the draft-07 schema, official references, local `REPARSE_DATA_BUFFER` structure evidence, no `HEAP_GENERATE_EXCEPTIONS` in `MountManagerHelpers.cpp`, checked `HeapAlloc` failure topology, `FSCTL_GET_REPARSE_POINT` bytes-returned gates, mount-point substitute-name nonzero/alignment/range gates, trailing-slash guard, `ImDiskOpenDeviceByName` preservation, zero-initialized `ImDiskQueryDeviceSize`, and ledger entry. `docs/plan/check-srev-135.sh` is the matrix wrapper.

Runtime/build gate: Windows service build for `MountManagerHelpers.cpp`, junction or volume mount-point smoke proving a valid substitute name still opens the target ImDisk device, malformed reparse payload injection proving invalid offset, length, alignment, and zero-length shapes return `INVALID_HANDLE_VALUE`, low-memory allocation fault injection proving `HeapAlloc` failure returns `ERROR_NOT_ENOUGH_MEMORY` without an unhandled exception, and ImDisk query failure smoke proving `ImDiskQueryDeviceSize` returns zero instead of an uninitialized value.
