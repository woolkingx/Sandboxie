# SREV-139: DeviceIoControl Deny IoStatus Completion

## Stage Gate

| Field | Value |
|---|---|
| Stage | action |
| Input artifact | `Sandboxie/core/drv/file_ctrl.c`, `Sandboxie/core/drv/syscall.c`, `Sandboxie/core/drv/syscall_open.c`, `Sandboxie/core/drv/file.c`, `Sandboxie/core/drv/process.h`, `Sandboxie/install/SbieSettings.ini`, Microsoft `ZwDeviceIoControlFile`, IOCTL layout, mount manager, Configuration Manager, and I/O status block references |
| Output artifact | `docs/plan/srev-139-deviceiocontrol-deny-iostatus.schema.json`, `docs/plan/check-srev-139.py`, `docs/plan/check-srev-139.sh`, ledger fragment |
| Owner | `Sandboxie/core/drv/file_ctrl.c` syscall-level `NtDeviceIoControlFile` filter |
| Acceptance gate | source checker plus full SREV/KPATH/core coverage matrix; Windows runtime proof remains required for DeviceIoControl callers using overlapped or native asynchronous paths |

## Evidence

`Sandboxie/core/drv/file_ctrl.c` is the next highest-ranked unnamed reviewable
core file after SREV-138. It is included by `syscall_open.c` and registered by
`syscall.c` as the handler for `DeviceIoControlFile`. The handler filters two
host-device control planes before forwarding to native `NtDeviceIoControlFile`:

- mount manager IOCTLs with device type `0x6d` and function numbers `0`, `1`,
  `3`, `6`, `7`, and `9`;
- Device Configuration Manager API (`\Device\DeviceApi\CMApi`) IOCTLs with
  device type `0x47`, unless `OpenDevCMApi` is enabled for the box.

Microsoft documents `ZwDeviceIoControlFile` / user-mode `NtDeviceIoControlFile`
as sending an IOCTL directly to the target device driver. Its `IoStatusBlock`
parameter receives final completion status and operation information. Microsoft
also documents IOCTL layout as `DeviceType`, `Access`, `Function`, and `Method`,
and documents `DEVICE_TYPE_FROM_CTL_CODE` and `METHOD_FROM_CTL_CODE` extraction
macros. Mount manager control codes are public documented `mountmgr.h` IOCTLs.
CMApi itself is not a public Microsoft wire protocol, but the public
Configuration Manager functions named in the local comments include mutation
operations such as disabling devices, setting devnode/device-interface
properties, registering interfaces, creating devnodes, uninstalling devnodes,
and deleting registry/class/interface keys.

Before this SREV, Sandboxie returned `STATUS_ACCESS_DENIED` directly for
blocked mount manager and CMApi IOCTLs. That denied the native call, but left
the caller-provided `IO_STATUS_BLOCK` untouched even though Sandboxie had become
the completion owner for that syscall. A stale status block can confuse native
or Win32 layers that inspect both the syscall status and `IoStatusBlock`.

Official references:

- https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntddk/nf-ntddk-zwdeviceiocontrolfile
- https://learn.microsoft.com/en-us/windows-hardware/drivers/kernel/defining-i-o-control-codes
- https://learn.microsoft.com/en-us/windows-hardware/drivers/kernel/i-o-status-blocks
- https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/ns-wdm-_io_status_block
- https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/mountmgr/
- https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/mountmgr/ni-mountmgr-ioctl_mountmgr_create_point
- https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/mountmgr/ni-mountmgr-ioctl_mountmgr_delete_points
- https://learn.microsoft.com/en-us/windows/win32/api/cfgmgr32/nf-cfgmgr32-cm_disable_devnode
- https://learn.microsoft.com/en-us/windows/win32/api/cfgmgr32/nf-cfgmgr32-cm_set_devnode_propertyw
- https://learn.microsoft.com/en-us/windows/win32/api/cfgmgr32/nf-cfgmgr32-cm_set_device_interface_propertyw

## Data

`user_args[0]` `FileHandle`, `user_args[4]` `PIO_STATUS_BLOCK`,
`user_args[5]` `IoControlCode`, `DEVICE_TYPE_FROM_CTL_CODE`,
`FUNCTION_FROM_CTL_CODE`, `METHOD_FROM_CTL_CODE`, mount manager device type
`0x6d`, CMApi device type `0x47`, `proc->file_open_devapi_cmapi`,
`OpenDevCMApi`, `STATUS_ACCESS_DENIED`, `IO_STATUS_BLOCK.Status`, and
`IO_STATUS_BLOCK.Information`.

## Schema

`DEVICEIOCONTROL_DENY_IOSTATUS_COMPLETION` says:

- `file_ctrl.c` owns syscall-level filtering before native
  `NtDeviceIoControlFile` sees blocked mount manager or CMApi IOCTLs.
- IOCTL routing is based on the official CTL_CODE bit layout plus local
  function denylist policy.
- CMApi function numbers remain a local policy projection because Microsoft does
  not publish the `\Device\DeviceApi\CMApi` wire protocol.
- When Sandboxie fabricates a final deny for `NtDeviceIoControlFile`, it must
  also become the completion owner for the caller's `IO_STATUS_BLOCK`.
- A fabricated deny writes `Status = STATUS_ACCESS_DENIED` and
  `Information = 0` before returning `STATUS_ACCESS_DENIED`.
- The write is guarded by `ProbeForWrite` and remains inside the outer syscall
  exception boundary.
- Allowed IOCTLs still flow to native `NtDeviceIoControlFile` unchanged.

## Topology

Legal denied flow:

```text
user NtDeviceIoControlFile args
  -> Syscall_DeviceIoControlFile
  -> decode IoControlCode by CTL_CODE fields
  -> blocked mountmgr or CMApi policy
  -> ProbeForWrite(IoStatusBlock)
  -> IoStatusBlock.Status = STATUS_ACCESS_DENIED
  -> IoStatusBlock.Information = 0
  -> return STATUS_ACCESS_DENIED
```

Legal allowed flow:

```text
user NtDeviceIoControlFile args
  -> Syscall_DeviceIoControlFile
  -> not blocked by mountmgr/CMApi policy
  -> native NtDeviceIoControlFile with original FileHandle, Event, APC,
     IoStatusBlock, control code, input buffer, and output buffer
```

## Logic Risk

This filter sits below Win32 compatibility layers and above native device
drivers. Returning only an `NTSTATUS` is not the full I/O completion shape for a
fabricated device-control result. The policy decision and the completion state
must agree, otherwise callers that reuse an `IO_STATUS_BLOCK` or inspect
`Information` can observe stale data from a prior I/O. The fix is local because
`file_ctrl.c` is the only owner that fabricates the mountmgr/CMApi denial.

This SREV does not reinterpret CMApi function numbers. Those remain a runtime
capture task because the device wire protocol is not public Microsoft API
surface.

## Fix

`file_ctrl.c` now uses `File_DenyDeviceIoControlFile` for both mount manager and
CMApi blocked paths. The helper probes the caller-provided `IO_STATUS_BLOCK`,
writes `STATUS_ACCESS_DENIED` and zero information, then returns the same
denial status.

The existing denylist, trace behavior, `OpenDevCMApi` compatibility switch, and
native pass-through path are unchanged.

## Acceptance Gate

`docs/plan/check-srev-139.py` validates the draft-07 schema, official reference
links, local syscall registration, `OpenDevCMApi` configuration ownership,
mount manager and CMApi denylist preservation, the new completion helper, both
blocked paths routing through the helper, absence of bare `STATUS_ACCESS_DENIED`
returns in `file_ctrl.c`, native pass-through preservation, and the ledger
fragment.

Runtime/build gate: Windows driver build; blocked mount manager IOCTL smoke
proving native callers receive `STATUS_ACCESS_DENIED` and `IO_STATUS_BLOCK`
`Status == STATUS_ACCESS_DENIED`, `Information == 0`; blocked CMApi mutation
smoke with `OpenDevCMApi=n`; compatibility smoke with `OpenDevCMApi=y`; and an
overlapped/native asynchronous caller check to confirm no event/APC regression.
