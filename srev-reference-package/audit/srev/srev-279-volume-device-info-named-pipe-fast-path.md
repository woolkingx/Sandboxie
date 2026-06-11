# SREV-279: Volume Device Info Named-Pipe Fast Path

| Field | Content |
|---|---|
| Stage | schema -> boundary -> verify |
| Input artifact | `Sandboxie/core/dll/file_dir.c`, KPATH-003, SREV-171, Microsoft `NtQueryVolumeInformationFile`, `FILE_FS_DEVICE_INFORMATION`, and device-type documentation |
| Output artifact | Source comment owner, draft-07 schema, checker, and ledger fragment |
| Owner | `File_NtQueryVolumeInformationFile` named-pipe `FileFsDeviceInformation` path |
| Acceptance gate | Targeted checker validates official references, named-pipe device-info fast path, KPATH-003/SREV-171 adjacency, stale hang wording removal, and ledger fragment |

## Data

`File_NtQueryVolumeInformationFile` handles hooked volume-information queries.
Before it calls path/box-root translation logic, it has a narrow fast path:

```text
FsInformationClass == FileFsDeviceInformation
Length >= sizeof(FILE_FS_DEVICE_INFORMATION)
native NtQueryVolumeInformationFile(FileFsDeviceInformation)
devInfo.DeviceType == FILE_DEVICE_NAMED_PIPE
copy devInfo to caller buffer
return status
```

The old comment described this as avoiding a named-pipe `NtQueryObject` hang.
KPATH-003 and SREV-171 now own the object-name routing fix in `obj.c`. This
SREV records the `file_dir.c` precedent as its own volume-info boundary:
`FileFsDeviceInformation` already answers the caller's requested shape, so the
hook can return without asking for an object path.

Runtime capture during the IPC bootstrap work found a second edge owned by this
hook: `Start.exe` entered `Ipc_IsKnownDllInSandbox`, then
`File_NtQueryVolumeInformationFile` recursively called `SbieDll_GetHandlePath`
from its sandbox-drive translation path until the TLS name-buffer depth guard
terminated the process. The volume-info hook now treats `ipc_KnownDlls_lock` and
its own `file_NtQueryVolumeInformation_lock` as native-volume-info routes,
preserving the normal first-level sandbox-drive translation while preventing
recursive handle-path lookup.

## Official Shape

Microsoft documents `NtQueryVolumeInformationFile(FileFsDeviceInformation)` as
returning a `FILE_FS_DEVICE_INFORMATION` structure. The output shape is selected
by `FsInformationClass`.

Microsoft documents `FILE_FS_DEVICE_INFORMATION` as providing the device type
associated with a file object. Its `DeviceType` member is the device object type
set by the driver.

Microsoft documents device type constants, including the named-pipe device type
used by the local `FILE_DEVICE_NAMED_PIPE` check.

Official references:

- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/nf-ntifs-ntqueryvolumeinformationfile`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/ns-wdm-_file_fs_device_information`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/kernel/specifying-device-types`

## Boundary

```text
caller asks FileFsDeviceInformation
  -> native volume-info query
  -> FILE_FS_DEVICE_INFORMATION.DeviceType
  -> named pipe device type
  -> return device-info buffer directly
```

The boundary is device-info classification, not object-name resolution.
`SbieDll_GetHandlePath` and `NtQueryObject(ObjectNameInformation)` are not the
owners of pipe identity when the caller only requested `FileFsDeviceInformation`.

KPATH-003 and SREV-171 own the broader object-name route. SREV-279 owns this
volume-info fast path and preserves it as the precedent that proved file/device
classification is the right route for named-pipe handles.

## Topology

```text
File_NtQueryVolumeInformationFile
  -> FileFsDeviceInformation + sufficient Length
  -> __sys_NtQueryVolumeInformationFile(... FileFsDeviceInformation)
  -> devInfo.DeviceType == FILE_DEVICE_NAMED_PIPE
  -> IoStatusBlock = native io status
  -> memcpy caller FsInformation
  -> return native status

otherwise
  -> normal Sandboxie volume/path translation path

recursive volume-info or KnownDll probe
  -> __sys_NtQueryVolumeInformationFile
  -> return native volume-info result
```

## Logic Risk

The old comment named the failure mode but not the owner boundary. A future edit
could remove the fast path as duplicated with KPATH-003/SREV-171, or could route
`FileFsDeviceInformation` through path lookup before answering the caller. That
would cross into a more dangerous owner even though the requested structure
already contains the needed device identity.

## Fix

The source now names SREV-279 and states that `FileFsDeviceInformation` is
enough to classify named-pipe handles, so the volume-info hook returns that
result directly rather than crossing into object-name resolution first. The hook
also has a narrow reentrancy gate: when a KnownDll sandbox probe or an existing
volume-info translation is already active, nested volume-info calls go straight
to `__sys_NtQueryVolumeInformationFile` instead of calling
`SbieDll_GetHandlePath` again.

## Acceptance Gate

`docs/plan/check-srev-279.py` validates the draft-07 schema, official
references, source fast-path shape, native volume-info call, `DeviceType ==
FILE_DEVICE_NAMED_PIPE` gate, `IoStatusBlock` and `FsInformation` propagation,
KPATH-003/SREV-171 adjacency, stale hang wording removal, and ledger fragment.

Runtime gate: Windows named-pipe volume-info matrix covering pending pipe I/O,
`FileFsDeviceInformation` direct queries, normal disk volume-info queries, and
object-name query paths covered by KPATH-003/SREV-171. IPC bootstrap smoke:
`Start.exe /box:New_Box /wait cmd.exe /c exit 0` must not emit
`SBIE2310` name-buffer overflow from `SbieDll_GetHandlePath`.
