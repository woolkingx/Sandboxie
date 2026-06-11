# SREV-109: MountManager ImBox State Boundaries

## Data

`Sandboxie/core/svc/MountManager.cpp` owns the service-side ImBox mount state
for encrypted file images and shared ram disks. It receives `MSGID_IMBOX_*`
messages over `PipeServer`, creates or discovers ImDisk-backed devices, creates
NTFS mount-point reparse records under the sandbox file root, optionally asks
the driver to protect a mounted root, and unmounts ImDisk devices when roots are
released.

The uncovered TODOs were all in this owner:

```text
constructor mounted-disk discovery
IMBOX_UPDATE unsupported image resize/password-rotation wire
recovered device protection-state query
mounting without a temporary drive letter
automatic BoxPassword use for configured file images
```

Those are related, but they do not share a small legal source fix. The current
local shape has distinct owners:

```text
m_RootMap              -> service in-memory reg/file-root ownership
BOX_MOUNT::Protected   -> set only after API_PROTECT_ROOT succeeds
FindImDisk             -> device recovery by ImBox proxy name
MountImDisk            -> temporary drive-letter + ImBox + fmifs format path
IMBOX_UPDATE_REQ       -> declared wire shape, no transaction implementation
password               -> caller-supplied request field, not durable config
```

## Official Shape

Microsoft documents mounted folders as an association between a volume and a
directory on another volume. Applications can access the target volume either
through the mounted-folder path or a drive letter.

Microsoft documents reparse points as application-defined data plus a tag. They
can be established on directories, but the directory must be empty; reparse data
has size limits; and mounted folders are implemented with reparse points.

Microsoft documents `FSCTL_SET_REPARSE_POINT`, `FSCTL_GET_REPARSE_POINT`, and
`FSCTL_DELETE_REPARSE_POINT` as caller-buffer operations over
`REPARSE_DATA_BUFFER` / `REPARSE_GUID_DATA_BUFFER`. Deleting a reparse point
requires the matching tag and does not delete the file or directory.

Microsoft documents `DeviceIoControl` as sending control codes directly to a
device driver, with input/output buffer sizes defined by the control code.

Microsoft documents `GetLogicalDrives` as returning a bitmask of currently
assigned drive letters. Cleared bits are drive letters not currently assigned
and therefore available for future mount points.

Microsoft documents `DefineDosDeviceW` as defining, redefining, or deleting
MS-DOS device names. `DDD_RAW_TARGET_PATH` uses the target path as-is;
`DDD_REMOVE_DEFINITION | DDD_EXACT_MATCH_ON_REMOVE` removes only the exact
mapping. Microsoft also says persistent drive-letter assignment should use
volume mount-point APIs rather than `DefineDosDevice`.

Microsoft documents mounted-folder enumeration as volume-scoped:
`FindFirstVolume` / `FindNextVolume` discover volumes; mounted folders on a
volume are found with `FindFirstVolumeMountPoint` /
`FindNextVolumeMountPoint`; those functions return mounted folders for a
specified volume, not arbitrary service-owned box-root state.

```text
https://learn.microsoft.com/en-us/windows/win32/fileio/volume-mount-points
https://learn.microsoft.com/en-us/windows/win32/fileio/reparse-points
https://learn.microsoft.com/en-us/windows-hardware/drivers/ifs/fsctl-set-reparse-point
https://learn.microsoft.com/en-us/windows-hardware/drivers/ifs/fsctl-get-reparse-point
https://learn.microsoft.com/en-us/windows-hardware/drivers/ifs/fsctl-delete-reparse-point
https://learn.microsoft.com/en-us/windows/win32/api/ioapiset/nf-ioapiset-deviceiocontrol
https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-getlogicaldrives
https://learn.microsoft.com/en-us/windows/win32/api/FileAPI/nf-fileapi-definedosdevicew
https://learn.microsoft.com/en-us/windows/win32/fileio/enumerating-volume-mount-points
```

## Schema

Local schema:

```text
docs/plan/srev-109-mountmanager-imbox-state-boundaries.schema.json
```

The ImBox mount-state boundary contract is:

```text
constructor does not rebuild m_RootMap from devices alone
FindImDisk recovers only ImDisk device identity by proxy name
reg_root and file_root ownership comes from IMBOX_MOUNT or AcquireBoxRoot requests
BOX_MOUNT::Protected becomes true only after API_PROTECT_ROOT succeeds
recovered ImDisk devices do not imply protected-root state
IMBOX_UPDATE remains unsupported until resize/password rotation has a transaction contract
MountImDisk requires a temporary drive-letter path for initial format
unrequested drive-letter mappings are removed after device discovery
BoxPassword is not read from durable config in AcquireBoxRoot
encrypted image mounts require caller-supplied password until secure handoff exists
```

## Topology

Explicit mount topology:

```text
SbieDll_Mount
  -> IMBOX_MOUNT_REQ(password, protect_root, admin_only, auto_unmount, reg_root, file_root)
  -> MountHandler
  -> FindImDisk(image file) or MountImDisk(image file, password)
  -> API_PROTECT_ROOT(reg_root, nt_path, admin_only) when requested
  -> m_RootMap[reg_root] = BOX_ROOT(file_root, BOX_MOUNT)
  -> CreateJunction(nt_path\Sandbox, file_root)
```

Automatic root acquisition topology:

```text
AcquireBoxRoot(boxname, reg_root, file_root)
  -> UseRamDisk / UseFileImage config
  -> SbieApi_QueryDrvInfo certificate option gate
  -> FindImDisk or MountImDisk
  -> m_RootMap[reg_root] = BOX_ROOT(file_root, BOX_MOUNT)
  -> CreateJunction(nt_path\Sandbox, file_root)
```

ImDisk mount topology:

```text
MountImDisk
  -> choose caller drive letter or ImDiskFindFreeDriveLetter
  -> launch ImBox with mount=<drive> and format=ntfs
  -> pass password through locked remote memory
  -> wait for ImBox event
  -> read returned \Device\ImDiskN path
  -> DefineDosDevice(... REMOVE_DEFINITION | EXACT_MATCH | RAW_TARGET_PATH) when drive was temporary
```

Recovery topology:

```text
FindImDisk(image file)
  -> enumerate ImDisk device numbers
  -> query ImBox proxy
  -> match proxy name derived from image file
  -> rebuild BOX_MOUNT NtPath/ImageFile only
```

## Logic Risk

The old comments made separate missing contracts look like local cleanup chores.
That is dangerous here. Mounted folders and reparse points have strict tag,
buffer, and empty-directory semantics; drive letters are namespace mappings;
and service mount state also includes Sandboxie-specific registry root,
file-root, protection, credential, and unmount policy.

Reconstructing `m_RootMap` from mounted devices alone would lose the reg-root
owner and protection policy. Querying the driver for `Protected` without a
scoped reg-root/device contract would create an ambiguous state read. Mounting
"without mount" conflicts with the current ImBox/fmifs format flow that uses a
temporary drive letter, then removes it when the caller did not request one.
Reading `BoxPassword` from durable config would turn an explicit credential
handoff into stored secret use without a secure credential contract.

## Fix

Comment-only source clarification:

```text
constructor device discovery is lazy through FindImDisk and cannot rebuild m_RootMap alone
IMBOX_UPDATE is unsupported until there is an ImBox transaction/protection refresh contract
recovered devices do not restore Protected state without explicit API_PROTECT_ROOT
temporary drive-letter use is required by the current ImBox format flow
AcquireBoxRoot does not read durable BoxPassword; encrypted images need caller credential handoff
```

No mount, unmount, ImDisk enumeration, `DefineDosDevice`, reparse-point,
password passing, driver protection, or wire-message behavior changed.

## Acceptance Gate

`docs/plan/check-srev-109.py` validates the draft-07 schema, official
references, removal of uncovered TODO comments, MountManager source comments,
explicit mount/acquire/recovery topology, temporary drive-letter cleanup,
unsupported update behavior, and ledger entry. `docs/plan/check-srev-109.sh` is
the matrix wrapper.

Runtime gate: Windows matrix with explicit encrypted image mount, automatic
`UseFileImage`, `UseRamDisk`, service restart with existing ImDisk device,
`protect_root` true/false, `admin_only` true/false, temporary drive-letter
allocation/removal, requested drive-letter preservation, `FSCTL_SET_REPARSE_POINT`
and `FSCTL_DELETE_REPARSE_POINT` behavior on empty/non-empty file roots, and
negative proof that `IMBOX_UPDATE` remains unsupported.
