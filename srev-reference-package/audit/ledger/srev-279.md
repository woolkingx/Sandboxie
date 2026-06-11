---
kind: srev-ledger-entry
id: SREV-279
title: Volume Device Info Named-Pipe Fast Path
status: patched-comment-topology-after-official-volume-device-info-named-pipe-review-no-behavior-change
owner: Sandboxie/core/dll/file_dir.c
spec: docs/plan/srev-279-volume-device-info-named-pipe-fast-path.md
schema: docs/plan/srev-279-volume-device-info-named-pipe-fast-path.schema.json
checker: docs/plan/check-srev-279.py
runtime_gate: Windows named-pipe FileFsDeviceInformation matrix
---

### SREV-279: Volume Device Info Named-Pipe Fast Path

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | patched source needs Windows runtime |
| Evidence | `File_NtQueryVolumeInformationFile` has a narrow fast path for `FileFsDeviceInformation` requests. It calls native `NtQueryVolumeInformationFile`, checks `FILE_FS_DEVICE_INFORMATION.DeviceType`, and if the handle is a named pipe, returns the device-info result directly. Runtime capture also showed `Start.exe` recursing through `File_NtQueryVolumeInformationFile -> SbieDll_GetHandlePath` during `Ipc_IsKnownDllInSandbox`, reaching `SBIE2310` before the target process launched. |
| Data | `File_NtQueryVolumeInformationFile`, `FsInformationClass`, `FileFsDeviceInformation`, `FILE_FS_DEVICE_INFORMATION`, `Length`, `__sys_NtQueryVolumeInformationFile`, `devInfo.DeviceType`, `FILE_DEVICE_NAMED_PIPE`, `IoStatusBlock`, `FsInformation`, `THREAD_DATA.file_NtQueryVolumeInformation_lock`, `THREAD_DATA.ipc_KnownDlls_lock`, KPATH-003, and SREV-171. |
| Schema | `VOLUME_DEVICE_INFO_NAMED_PIPE_FAST_PATH` says `File_NtQueryVolumeInformationFile` owns the named-pipe `FileFsDeviceInformation` fast path; `NtQueryVolumeInformationFile` output shape is selected by `FsInformationClass`; `FileFsDeviceInformation` returns `FILE_FS_DEVICE_INFORMATION`; `DeviceType` identifies the associated device object type; `DeviceType == FILE_DEVICE_NAMED_PIPE` is enough to answer this volume-info query; the hook must not route this class through object-name resolution before returning the named-pipe device result; recursive volume-info and KnownDll-probe volume-info calls route directly to native volume info; KPATH-003 and SREV-171 own broader object-name routing for named-pipe handles. |
| Topology | `FileFsDeviceInformation + sufficient Length -> native volume-info query -> FILE_FS_DEVICE_INFORMATION.DeviceType -> FILE_DEVICE_NAMED_PIPE -> copy IoStatusBlock and FsInformation -> return`. `ipc_KnownDlls_lock` or `file_NtQueryVolumeInformation_lock -> __sys_NtQueryVolumeInformationFile -> return`. Non-named-pipe first-level volume-info requests continue into normal Sandboxie volume/path translation. |
| Logic Risk | A future edit could remove this fast path as duplicated with object-name handling, or could answer `FileFsDeviceInformation` only after path lookup. A nested volume-info query during handle-path translation can also recurse back into `SbieDll_GetHandlePath` and trip the name-buffer depth guard. |
| Official Shape | Microsoft documents `NtQueryVolumeInformationFile(FileFsDeviceInformation)` as returning `FILE_FS_DEVICE_INFORMATION`. Microsoft documents `FILE_FS_DEVICE_INFORMATION.DeviceType` as the associated device object type. Microsoft device-type documentation supplies the named-pipe device type used by the local `FILE_DEVICE_NAMED_PIPE` gate. |
| Fix | The source now names SREV-279 and states that `FileFsDeviceInformation` is enough to classify named-pipe handles, so the volume-info hook returns that result directly rather than crossing into object-name resolution first. The hook also adds `file_NtQueryVolumeInformation_lock` and routes nested volume-info calls, including KnownDll sandbox-probe volume-info calls, directly to `__sys_NtQueryVolumeInformationFile`. |
| Acceptance Gate | `docs/plan/check-srev-279.py` validates the draft-07 schema, official references, source fast-path shape, native volume-info call, `DeviceType == FILE_DEVICE_NAMED_PIPE` gate, `IoStatusBlock` and `FsInformation` propagation, reentrancy lock, KnownDll native-volume-info route, KPATH-003/SREV-171 adjacency, stale hang wording removal, and ledger fragment; `docs/plan/check-srev-279.sh` is the targeted wrapper. Runtime gate: Windows named-pipe volume-info matrix covering pending pipe I/O, `FileFsDeviceInformation` direct queries, normal disk volume-info queries, object-name query paths covered by KPATH-003/SREV-171, and IPC bootstrap smoke without `SBIE2310` from `SbieDll_GetHandlePath`. |
