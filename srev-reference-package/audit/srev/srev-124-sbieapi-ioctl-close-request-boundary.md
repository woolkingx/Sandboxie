# SREV-124 SbieApi Ioctl Close Request Boundary

## Data

Owner file:

```text
Sandboxie/core/dll/sbieapi.c
```

Reviewed nodes:

```text
SbieApi_Ioctl
parms
SbieApi_DeviceHandle
INVALID_HANDLE_VALUE
NtClose
NtOpenFile
NtDeviceIoControlFile
__sys_NtDeviceIoControlFile
API_SBIEDRV_CTLCODE
Dll_SbieTrace
SbieApi_MonitorPutMsg
STATUS_SERVER_DISABLED
```

## Schema

`SBIEAPI_IOCTL_CLOSE_REQUEST_BOUNDARY` defines these local contracts:

- `SbieApi_Ioctl(NULL)` is a close request used by kmdutil.
- A null `parms` close request closes the cached driver handle when one exists.
- A null `parms` close request always invalidates `SbieApi_DeviceHandle`.
- A null `parms` close request returns before trace, open, or device-ioctl
  logic can read `parms[0]` or reopen the driver device.
- A non-null `parms` request preserves the existing trace, driver-open,
  `STATUS_SERVER_DISABLED` remap, hook-bypass, and ioctl call topology.
- The close request reports `NtClose` status when a handle existed, otherwise
  `STATUS_SUCCESS`.

## Topology

```text
SbieApi_Ioctl(NULL)
  -> optional NtClose(SbieApi_DeviceHandle)
  -> SbieApi_DeviceHandle = INVALID_HANDLE_VALUE
  -> return close status

SbieApi_Ioctl(non-null parms)
  -> optional trace using parms[0]
  -> NtOpenFile(API_DEVICE_NAME) when cached handle is invalid
  -> status remap for missing driver device
  -> __sys_NtDeviceIoControlFile or NtDeviceIoControlFile
  -> return ioctl status
```

## Logic Risk

The old close-request branch closed and invalidated the cached device handle
but then fell through into the trace and ioctl path. That made `parms == NULL`
both a null-pointer read risk at `parms[0]` and a contradictory state transition:
a close request could immediately reopen the driver device and issue an ioctl
with a null input buffer.

The correct local repair is to make the close request a terminal transition at
the cached-handle owner boundary. It does not change normal API request
marshalling, trace filtering, driver open access, missing-driver status remap,
or the hooked/native `NtDeviceIoControlFile` selection.

## Official Shape

- https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-zwclose
- https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/nf-ntifs-ntopenfile
- https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/nf-ntifs-ntdeviceiocontrolfile
- https://learn.microsoft.com/en-us/windows-hardware/drivers/kernel/using-nt-and-zw-versions-of-the-native-system-services-routines

## Fix

`SbieApi_Ioctl(NULL)` now initializes `status` to `STATUS_SUCCESS`, calls
`NtClose` only when a cached handle exists, invalidates the global cached
handle, and returns immediately. If `NtClose` ran, its status is returned to the
caller.

The non-null request path is unchanged: tracing still reads `parms[0]`, the
driver device is opened lazily through `NtOpenFile`, missing driver statuses
still map to `STATUS_SERVER_DISABLED`, and ioctl dispatch still uses
`__sys_NtDeviceIoControlFile` when available before falling back to
`NtDeviceIoControlFile`.

## Acceptance Gate

Source gate:

```bash
python3 docs/plan/check-srev-124.py
bash docs/plan/check-srev-124.sh
```

Runtime/build gate still required:

- Windows build for `sbieapi.c`.
- kmdutil close-request smoke proving `SbieApi_Ioctl(NULL)` closes an existing
  cached handle and does not call trace, `NtOpenFile`, or `NtDeviceIoControlFile`.
- Null close-request smoke with no cached handle proving `STATUS_SUCCESS` and no
  driver reopen.
- Positive normal API call smoke proving unchanged trace filtering, lazy driver
  open, missing-driver remap, hook-bypass selection, and ioctl request buffer
  shape.
