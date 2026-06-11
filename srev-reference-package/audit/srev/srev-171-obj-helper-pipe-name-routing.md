# SREV-171: Object Name Helper Pipe Routing

## Stage Gate

```text
stage: schema -> boundary -> topology -> logic -> action -> verify
input artifact: Sandboxie/core/dll/obj.c, KPATH-003, file_dir.c named-pipe precedent, and Microsoft object/file device information documentation
output artifact: Obj_GetObjectName shares the same named-pipe-safe route as Obj_NtQueryObject; Windows named-pipe runtime proof remains open
owner: Sandboxie/core/dll/obj.c
acceptance gate: docs/plan/check-srev-171.py and docs/plan/check-srev-171.sh
```

## Data

`obj.c` owns user-mode object-name mediation for Sandboxie DLL hooks. It has
two paths that can ask for an object name:

- `Obj_NtQueryObject` intercepts external `NtQueryObject(ObjectNameInformation)`
  calls, classifies supported object types, rewrites file/key/ipc names, and now
  routes named-pipe File handles through driver lookup.
- `Obj_GetObjectName` is an internal helper used by file, key, ipc, and security
  code when a root handle or arbitrary handle must be converted into an object
  name.

KPATH-003 already documented the native pipe-name hang risk and patched
`Obj_NtQueryObject`. This SREV closes the same risk in the internal helper
route.

## Official Shape

- Microsoft documents `NtQueryObject` as a native object-information routine
  that may change or be removed, and its Win32 page documents basic/type object
  information rather than making object-name lookup the owner of file/pipe
  identity:
  `https://learn.microsoft.com/en-us/windows/win32/api/winternl/nf-winternl-ntqueryobject`.
- Microsoft documents `GetFileType` as returning `FILE_TYPE_PIPE` for sockets,
  named pipes, or anonymous pipes. Pipe identity is therefore a file-handle
  classification:
  `https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-getfiletype`.
- Microsoft documents `NtQueryVolumeInformationFile(FileFsDeviceInformation)`
  as returning `FILE_FS_DEVICE_INFORMATION` for the volume associated with a
  file, directory, storage device, or volume:
  `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/nf-ntifs-ntqueryvolumeinformationfile`.
- Microsoft documents `FILE_FS_DEVICE_INFORMATION.DeviceType` as the type of
  the device object associated with a file object:
  `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/ns-wdm-_file_fs_device_information`.
- Microsoft defines `FILE_DEVICE_NAMED_PIPE` as device type `0x00000011`:
  `https://learn.microsoft.com/en-us/windows-hardware/drivers/kernel/specifying-device-types`.

## Schema

`OBJ_HELPER_PIPE_NAME_ROUTING` says:

- `obj.c` owns both the hooked `Obj_NtQueryObject` route and the internal
  `Obj_GetObjectName` helper route.
- Native `NtQueryObject(ObjectTypeInformation)` may classify the Object Manager
  object type, but native `NtQueryObject(ObjectNameInformation)` is not the
  owner of pipe/file identity.
- File handles that may be named pipes must be classified with
  `NtQueryVolumeInformationFile(FileFsDeviceInformation)` and
  `FILE_FS_DEVICE_INFORMATION.DeviceType`.
- If `DeviceType == FILE_DEVICE_NAMED_PIPE`, the name route must use
  `Obj_GetObjectNameFromDriver` instead of native
  `NtQueryObject(ObjectNameInformation)`.
- `UseDriverObjLookup` remains a broader compatibility setting that routes all
  helper lookups through the driver.
- If a driver-routed name query fails, the route must not fall back to the same
  native object-name query that it was avoiding.
- Linux source gates are not Windows named-pipe hang reproduction or
  compatibility proof.

## Topology

Legal helper topology after this SREV:

```text
Obj_GetObjectName(handle)
  -> UseDriverObjLookup? yes -> Obj_GetObjectNameFromDriver
  -> no
  -> Obj_GetObjectType(handle)
  -> File?
     -> NtQueryVolumeInformationFile(FileFsDeviceInformation)
     -> FILE_DEVICE_NAMED_PIPE?
        -> Obj_GetObjectNameFromDriver
        -> no native object-name fallback
  -> non-pipe or non-File
     -> native NtQueryObject(ObjectNameInformation)
```

The existing hooked topology remains:

```text
Obj_NtQueryObject(ObjectNameInformation)
  -> Obj_GetObjectType
  -> File?
     -> UseDriverObjLookup or named-pipe device classification
     -> driver lookup if true
  -> rewrite file/key/ipc names
  -> return caller-shaped OBJECT_NAME_INFORMATION
```

## Logic Risk

Before this SREV, `Obj_GetObjectName` carried the same comment-admitted
native-name-query hang risk as KPATH-003, but only avoided it when the global
`UseDriverObjLookup` setting was enabled. Internal callers such as root-handle
path construction can receive File handles, including anonymous or named pipe
handles. Leaving the helper on native `NtQueryObject(ObjectNameInformation)` for
named-pipe File handles preserved a second route into the same hang class after
the external hook path had been hardened.

## Action

`Obj_GetObjectName` now routes through `Obj_GetObjectNameFromDriver` when either
`UseDriverObjLookup` is enabled or the handle is a File object whose
`FileFsDeviceInformation` reports `FILE_DEVICE_NAMED_PIPE`. Non-pipe and
non-File helper lookups keep the existing native `NtQueryObject` route.

No driver API packing, SbieApi wire shape, key/ipc/file rewrite logic, or
`Obj_NtQueryObject` caller buffer copy semantics are changed.

## Verification

Source-level gates:

```bash
python3 docs/plan/check-srev-171.py
bash docs/plan/check-srev-171.sh
python3 docs/plan/check-core-coverage.py
```

Full closure matrix:

```bash
python3 docs/plan/check-srev-171.py &&
bash docs/plan/check-srev-171.sh &&
python3 docs/plan/check-core-coverage.py &&
for s in docs/plan/check-srev-0*.sh docs/plan/check-srev-1*.sh docs/plan/check-kpath-0*.sh; do bash "$s"; done &&
git diff --check
```

Runtime gate: Windows build plus a sandboxed named-pipe repro where a
synchronous pipe handle with a pending read is passed through both
`NtQueryObject(ObjectNameInformation)` and an internal helper path such as
root-handle path construction; neither route may hang, normal file/key/ipc name
rewriting must still work, and failed driver-routed pipe lookups must not fall
back to native object-name query.
