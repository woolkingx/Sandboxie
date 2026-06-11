# SREV-275: File Rename Cross-Volume Gate

| Field | Content |
|---|---|
| Stage | schema -> topology -> verify |
| Input artifact | `Sandboxie/core/dll/file.c`, `Sandboxie/core/drv/file.c`, Microsoft `FILE_RENAME_INFORMATION`, `NtSetInformationFile`, `FltSetInformationFile`, and Win32 `MoveFileEx` documentation |
| Output artifact | Source comment owner, draft-07 schema, checker, and ledger fragment |
| Owner | `File_RenameOpenFile`, `File_RenameFile`, and `File_Api_Rename` NT rename routing |
| Acceptance gate | Targeted checker validates official references, same-volume rename contract, Win32 copy/delete fallback boundary, driver API rename projection, stale FIXME removal, and ledger fragment |

## Data

Three Sandboxie rename paths issue NT rename requests and carried local FIXME
comments about `STATUS_NOT_SAME_DEVICE`:

- `File_RenameOpenFile` builds a `FILE_RENAME_INFORMATION` buffer with
  `RootDirectory = dir_handle` for the target parent directory.
- `File_RenameFile` builds either `FILE_RENAME_INFORMATION` or
  `FILE_LINK_INFORMATION` after resolving true/copy source and target paths,
  then issues `FileRenameInformation` or `FileLinkInformation`.
- `File_Api_Rename` receives `API_RENAME_FILE_ARGS`, opens the target parent
  directory, reopens the source file object as a kernel handle, then calls
  `ZwSetInformationFile(..., FileRenameInformation)`.

The source comments treated `STATUS_NOT_SAME_DEVICE` as a possible odd case.
The official API shape says it is the legal NT rename boundary: a rename cannot
move a file or directory to a different volume.

## Official Shape

Microsoft documents `FILE_RENAME_INFORMATION` as the structure used to rename a
file. The rename target can be a simple file name, a fully qualified file name,
or a relative file name plus `RootDirectory`. General rename rules state that a
file or directory can only be renamed within a volume.

Microsoft documents `NtSetInformationFile` / `ZwSetInformationFile` as selecting
the concrete `FileInformation` buffer structure from `FileInformationClass`;
`FileRenameInformation` supplies a `FILE_RENAME_INFORMATION` buffer.

Microsoft documents `FltSetInformationFile` rename behavior for minifilters and
states that callers are responsible for ensuring the new name is on the same
volume as the old name.

Microsoft documents `MoveFileEx` `MOVEFILE_COPY_ALLOWED` as the Win32 layer
that can simulate a cross-volume move by copying and deleting.

Official references:

- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/ns-ntifs-_file_rename_information`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/nf-ntifs-ntsetinformationfile`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/fltkernel/nf-fltkernel-fltsetinformationfile`
- `https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-movefileexa`

## Boundary

```text
Win32 MoveFileEx / caller policy
  -> may choose MOVEFILE_COPY_ALLOWED
  -> NtSetInformationFile(FileRenameInformation)
  -> NT same-volume rename gate
  -> STATUS_NOT_SAME_DEVICE if the target crosses a volume
```

Sandboxie's DLL hook owns the copy-path and open-path projection for the NT
rename request. Sandboxie's driver API owns the `API_RENAME_FILE` projection
from the service/client request into `ZwSetInformationFile`. Neither owner owns
the high-level cross-volume move policy. If the caller is a Win32 move API
using `MOVEFILE_COPY_ALLOWED`, preserving the NT failure lets that upper layer
decide whether to copy and delete.

## Topology

```text
File_RenameOpenFile
  -> open target parent directory
  -> FILE_RENAME_INFORMATION.RootDirectory = dir_handle
  -> NtSetInformationFile(FileRenameInformation)
  -> same-volume gate

File_RenameFile
  -> resolve source/target true and copy paths
  -> open source and target parent handles
  -> FILE_RENAME_INFORMATION or FILE_LINK_INFORMATION
  -> NtSetInformationFile(FileRenameInformation/FileLinkInformation)
  -> sharing retry if needed
  -> same-volume gate for rename

File_Api_Rename
  -> API_RENAME_FILE counted target path/name
  -> open target parent directory
  -> reopen caller file object as kernel handle
  -> FILE_RENAME_INFORMATION.RootDirectory = dir_handle
  -> ZwSetInformationFile(FileRenameInformation)
  -> same-volume gate
```

## Logic Risk

The stale FIXME wording made `STATUS_NOT_SAME_DEVICE` look like a defect the
hook should hide. That would be the wrong owner boundary: implementing copy and
delete inside the NT rename hook would duplicate Win32 `MOVEFILE_COPY_ALLOWED`
policy, change security descriptor / ACL behavior, and blur rename versus copy
semantics.

## Fix

Comment-only source clarification. All three FIXME blocks now name SREV-275 and
state that `FILE_RENAME_INFORMATION` is an NT same-volume operation. The hook
and driver API preserve `STATUS_NOT_SAME_DEVICE` so the caller or Win32 layer
can decide whether to use copy/delete fallback. No behavior changed.

## Acceptance Gate

`docs/plan/check-srev-275.py` validates the draft-07 schema, official
references, all three source comment owners, `File_RenameOpenFile`,
`File_RenameFile`, and `File_Api_Rename` rename issue sites, sharing retry
preservation, stale FIXME removal, `MOVEFILE_COPY_ALLOWED` boundary
documentation, and ledger fragment.

Runtime gate: Windows rename/move matrix covering same-directory rename,
same-volume cross-directory rename, open-path target rename, cross-volume
rename returning `STATUS_NOT_SAME_DEVICE`, and Win32 `MoveFileEx` with and
without `MOVEFILE_COPY_ALLOWED`.
