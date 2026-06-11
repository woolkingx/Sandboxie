# SREV-019 Rename/Link Target Length Shape

Status: source-level spec before patch.

## Official Shape

Microsoft documents both `FILE_RENAME_INFORMATION` and `FILE_LINK_INFORMATION`
as variable-size structures whose `FileNameLength` member is an `ULONG` byte
count and whose `FileName[1]` member starts a wide-character name payload.

For minifilter `IRP_MJ_SET_INFORMATION` callbacks, `FLT_PARAMETERS` exposes
`SetFileInformation.Length` as the byte length of the `InfoBuffer`, and
`SetFileInformation.InfoBuffer` as the input buffer containing the file
information to set. The same union describes `ParentOfTarget` as the target
parent file object for rename and link operations when the target is qualified
or rooted.

`FltSetInformationFile` also documents that its `Length` parameter is the byte
size of the information buffer and that minifilters must use
`FltSetInformationFile` rather than `ZwSetInformationFile` for rename/link set
operations. It specifically notes that `FltSetInformationFile` does not
validate every `FILE_RENAME_INFORMATION` content rule for the caller.

Sources:

- https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/ns-ntifs-_file_rename_information
- https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/ns-ntifs-_file_link_information
- https://learn.microsoft.com/en-us/windows-hardware/drivers/ifs/flt-parameters-for-irp-mj-set-information
- https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/fltkernel/nf-fltkernel-fltsetinformationfile

## Local Shape

`File_RenameOperation` receives a minifilter set-information request and turns
the target file-name payload into a `UNICODE_STRING` for
`File_Generic_MyParseProc`.

That local parser shape is narrower than the official incoming structure:

- incoming `FileNameLength`: `ULONG` bytes
- local `UNICODE_STRING.Length`: `USHORT` bytes

## Local Risk

The previous implementation cast the official `ULONG` byte count directly to
`USHORT`. A target name longer than `MAXUSHORT` bytes can wrap before the policy
parser sees it. That makes the policy decision observe a shorter byte range
than the filesystem operation requested.

The same parser must not trust `FileNameLength` unless the bytes fit inside
`SetFileInformation.Length`, because the InfoBuffer is the boundary carrier.

## Patch Boundary

Keep the existing minifilter policy path and fail closed for shapes this parser
cannot faithfully represent as `UNICODE_STRING`.

Before constructing the `UNICODE_STRING`, reject rename/link target names when:

- `FileNameLength` is zero
- `FileNameLength > MAXUSHORT`
- `FileNameLength` is not WCHAR-byte aligned
- `FIELD_OFFSET(..., FileName) + FileNameLength` does not fit inside
  `SetFileInformation.Length`

## Acceptance Gate

- The `ULONG` name length is range-checked before any cast to `USHORT`.
- The name bytes are proven to fit inside `SetFileInformation.InfoBuffer`.
- Odd byte lengths are rejected before the wide-character parser sees them.
- Runtime gate remains open: long rename/link attempts and malformed
  InfoBuffers must fail closed, while ordinary rename and hard-link operations
  still pass the existing policy path on Windows.
