# SREV-274: File Hard-Link Class Boundary

| Field | Content |
|---|---|
| Stage | schema -> boundary -> verify |
| Input artifact | `Sandboxie/core/dll/file.c`, `Sandboxie/core/drv/file_flt.c`, Microsoft `NtSetInformationFile`, `FILE_LINK_INFORMATION`, `FILE_LINKS_INFORMATION`, and `NtQueryInformationFile` documentation |
| Output artifact | Source comment owner, draft-07 schema, checker, and ledger fragment |
| Owner | `File_NtSetInformationFile` hard-link set request routing |
| Acceptance gate | Targeted checker validates official references, FileLink/HardLink class separation, driver denial adjacency, stale todo removal, and ledger fragment |

## Data

`File_NtSetInformationFile` handles selected file set-information classes:

- `FileBasicInformation` routes to `File_SetAttributes`.
- `FileDispositionInformation` and `FileDispositionInformationEx` route to
  `File_SetDisposition`.
- `FileRenameInformation` and `FileRenameInformationEx` route to
  `File_RenameFile(..., FALSE)`.
- `FileLinkInformation` and `FileLinkInformationEx` route to
  `File_RenameFile(..., TRUE)`.
- `FileHardLinkInformation` and `FileHardLinkFullIdInformation` currently take
  a native compatibility probe through `__sys_NtSetInformationFile`. If that
  probe fails, the hook returns `STATUS_INVALID_DEVICE_REQUEST` so callers that
  can fall back to copy behavior may do so.

`Sandboxie/core/drv/file_flt.c` is the adjacent kernel minifilter owner for
`IRP_MJ_SET_INFORMATION`. It only routes `FileLinkInformation` and
`FileLinkInformationEx` into `File_RenameOperation(..., TRUE)`; alternate
hard-link classes are denied in that branch.

## Official Shape

Microsoft documents `NtSetInformationFile` as receiving a `FileInformation`
buffer whose concrete structure is determined by `FileInformationClass`.
`FileLinkInformation` creates a hard link to an existing file and uses a
`FILE_LINK_INFORMATION` buffer.

Microsoft documents `FILE_LINK_INFORMATION` as the structure used to create an
NTFS hard link. On newer Windows versions its first field is a union:
`ReplaceIfExists` for `FileLinkInformation` and `Flags` for
`FileLinkInformationEx`.

Microsoft documents `NtQueryInformationFile(FileHardLinkInformation)` as
returning `FILE_LINKS_INFORMATION`, and `FILE_LINKS_INFORMATION` describes a
list-style link information buffer with `BytesNeeded`, `EntriesReturned`, and
`FILE_LINK_ENTRY_INFORMATION`.

Official references:

- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/nf-ntifs-ntsetinformationfile`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/ns-ntifs-_file_link_information`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/nf-ntifs-ntqueryinformationfile`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/ns-ntifs-_file_links_information`

## Boundary

```text
caller NtSetInformationFile
  -> FileInformationClass
  -> class-specific FileInformation buffer
  -> Sandboxie hard-link routing
```

The legal local create-hard-link path is only the `FILE_LINK_INFORMATION` shape
used by `FileLinkInformation` and `FileLinkInformationEx`. The alternate
`FileHardLinkInformation` and `FileHardLinkFullIdInformation` names must not be
folded into `File_RenameFile(..., TRUE)` without proving their setter buffer
shape and kernel filter behavior.

## Topology

```text
FileLinkInformation / FileLinkInformationEx
  -> FILE_LINK_INFORMATION / FILE_LINK_INFORMATION_EX-compatible buffer
  -> File_RenameFile(..., TRUE)
  -> copy-path-aware hard-link creation

FileHardLinkInformation / FileHardLinkFullIdInformation
  -> no local class-specific setter parser in this hook
  -> native compatibility probe
  -> failure becomes STATUS_INVALID_DEVICE_REQUEST
  -> file_flt.c denies these alternate classes for sandboxed IRP_MJ_SET_INFORMATION
```

## Logic Risk

The stale `else // todo` hid a class-boundary decision. A future edit could
merge `FileHardLinkInformation` into the `FileLinkInformation` code path because
both names mention hard links. That would be schema-wrong unless the alternate
class's set-information buffer shape, length gate, root-directory handling, and
minifilter topology are proven first.

## Fix

Comment-only source clarification. The bare `else // todo` now names SREV-274
and records that only `FileLinkInformation` / `FileLinkInformationEx` have the
local `FILE_LINK_INFORMATION` create-hard-link path. The alternate hard-link
classes remain a native compatibility probe until a class-specific setter
contract is proven. No behavior changed.

## Acceptance Gate

`docs/plan/check-srev-274.py` validates the draft-07 schema, official
references, `File_NtSetInformationFile` hard-link class routing, native
compatibility probe preservation, `STATUS_INVALID_DEVICE_REQUEST` fallback,
driver minifilter denial adjacency, stale todo removal, and ledger fragment.

Runtime gate: Windows hard-link set-information matrix covering
`FileLinkInformation`, `FileLinkInformationEx`, `FileHardLinkInformation`, and
`FileHardLinkFullIdInformation`, with sandboxed inside-box, outside-box,
cross-volume, existing-target, and caller fallback behavior.
