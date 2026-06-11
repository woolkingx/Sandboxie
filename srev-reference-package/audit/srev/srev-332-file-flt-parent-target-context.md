# SREV-332: File Filter ParentOfTarget Context

| Field | Content |
|---|---|
| Stage | schema -> topology -> verify |
| Input artifact | `Sandboxie/core/drv/file_flt.c`, Microsoft `FLT_PARAMETERS` for `IRP_MJ_SET_INFORMATION`, `FILE_RENAME_INFORMATION`, `FILE_LINK_INFORMATION`, and `FltSetInformationFile` documentation |
| Output artifact | Source comment owner, draft-07 schema, checker, and ledger fragment |
| Owner | `File_PreOperation` set-information routing and `File_RenameOperation` target-context parser |
| Acceptance gate | Targeted checker validates official references, ParentOfTarget carrier shape, RelatedFileObject fallback, stale bug wording removal, and ledger fragment |

## Data

The `IRP_MJ_SET_INFORMATION` branch in `File_PreOperation` had a commented-out
alternative hard-link check that tried to inspect
`Iopb->Parameters.SetFileInformation.ParentOfTarget->FileName` directly and
noted that it "does not contain device path".

The active code does not use that disabled direct check. It routes
`FileLinkInformation` / `FileLinkInformationEx` and
`FileRenameInformation` / `FileRenameInformationEx` into
`File_RenameOperation`, which:

- requires `SetFileInformation.ParentOfTarget`;
- validates the counted `FILE_LINK_INFORMATION` or `FILE_RENAME_INFORMATION`
  target name through SREV-019 length gates;
- builds a target-name `UNICODE_STRING`;
- replaces a relative `ParentOfTarget` file object with its full-path
  `RelatedFileObject` when available;
- calls `File_Generic_MyParseProc` with the file object, device type, relative
  target name, and `IO_OPEN_TARGET_DIRECTORY` context.

## Official Shape

Microsoft documents `FLT_PARAMETERS.SetFileInformation.ParentOfTarget` as a
file object pointer for rename or link target parent directories when the
target name is fully qualified or rooted. It is not documented as a complete
device-path string.

Microsoft documents `FILE_RENAME_INFORMATION` and `FILE_LINK_INFORMATION` as
carrying a `RootDirectory` plus `FileNameLength` and `FileName`. The name may be
simple, fully qualified, or relative according to the root-directory shape.

Microsoft documents `FltSetInformationFile` as the minifilter routine for
setting rename/link information, with `Length` as the byte size of the
file-information buffer.

Official references:

- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ifs/flt-parameters-for-irp-mj-set-information`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/ns-ntifs-_file_rename_information`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/ns-ntifs-_file_link_information`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/fltkernel/nf-fltkernel-fltsetinformationfile`

## Boundary

```text
IRP_MJ_SET_INFORMATION
  -> FLT_PARAMETERS.SetFileInformation
  -> ParentOfTarget file object + InfoBuffer target name
  -> File_RenameOperation
  -> File_Generic_MyParseProc
```

The legal boundary is object context plus counted target name. Treating
`ParentOfTarget->FileName` as the entire target path is schema-wrong because
`ParentOfTarget` is a file object pointer, and its `FileName` can be relative to
another object.

## Topology

```text
File_PreOperation
  -> FileLinkInformation/FileLinkInformationEx
  -> File_RenameOperation(..., TRUE)

File_PreOperation
  -> FileRenameInformation/FileRenameInformationEx
  -> File_RenameOperation(..., FALSE)

File_RenameOperation
  -> ParentOfTarget file object
  -> FILE_*_INFORMATION.FileName counted target name
  -> optional RelatedFileObject full-path context
  -> File_Generic_MyParseProc(..., IO_OPEN_TARGET_DIRECTORY)
```

## Logic Risk

The stale disabled comment made the issue look like a missing string prefix
patch on `ParentOfTarget->FileName`. The stronger interpretation is that
`ParentOfTarget` is not the string owner. It is a file-object carrier whose
relative/full path context must be combined with the counted target name before
policy parsing.

## Fix

Comment-only source clarification. The disabled old direct check now names
SREV-332 and says `ParentOfTarget` is a file-object carrier while
`File_RenameOperation` owns target-context parsing. No set-information class
predicate, length gate, `RelatedFileObject` fallback, parser call, or return
status changed.

## Acceptance Gate

`docs/plan/check-srev-332.py` validates the draft-07 schema, official
references, source routing from set-information classes to `File_RenameOperation`,
the `ParentOfTarget` requirement, SREV-019 length gates, `RelatedFileObject`
fallback, `File_Generic_MyParseProc` target-directory context, stale bug wording
removal, combined ledger entry, and split ledger fragment.

Runtime gate: Windows rename/link matrix covering rooted target parent,
relative target parent, network-drive related-file-object fallback, inside-box
target, outside-box target denial, and SREV-019 long/malformed name regression.
