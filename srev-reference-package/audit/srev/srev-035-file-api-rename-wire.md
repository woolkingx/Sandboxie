# SREV-035: File API Rename Counted String

## Finding

`Sandboxie/core/drv/file.c` receives `API_RENAME_FILE_ARGS.target_dir` and
`target_name` as user `UNICODE_STRING64*` values. The driver path treated
`Length` as a byte count only partially: odd byte counts were silently rounded
down with `& ~1`, copied counted bytes were then interpreted with `wcslen` and
`wcschr`, and the malformed-name branch after `path` allocation returned without
freeing `path`.

## Official Shape

- `UNICODE_STRING.Length` is the length in bytes of the string stored in
  `Buffer`; when the string is NUL-terminated, `Length` does not include the
  trailing NUL:
  `https://learn.microsoft.com/en-us/windows/win32/api/ntdef/ns-ntdef-_unicode_string`
- `ProbeForRead` validates a user buffer range using a byte length and required
  alignment:
  `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-probeforread`
- `ZwSetInformationFile` receives a `FileInformation` buffer and a byte `Length`
  for the selected information class:
  `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-zwsetinformationfile`
- `FILE_RENAME_INFORMATION.FileNameLength` is the byte length of `FileName`; with
  a non-NULL `RootDirectory`, `FileName` is the simple relative target name:
  `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/ns-ntifs-_file_rename_information`

## Local Schema

Machine-readable schema:

```text
docs/plan/srev-035-file-api-rename-wire.schema.json
```

The local driver API accepts counted WCHAR byte strings from user mode. Legal
input must be non-empty, WCHAR-aligned, within the local 32000-byte cap, and not
larger than `MaximumLength`. Because the implementation later uses C-string path
APIs after copying into a NUL-padded kernel buffer, embedded NULs are rejected
instead of being allowed to truncate the probed byte range. `target_name` is a
simple relative rename name under `RootDirectory`, so it must not contain `\`.

## Fix

`File_Api_Rename` now rejects odd byte lengths instead of rounding them down,
checks `Length <= MaximumLength`, scans counted WCHAR segments for embedded NUL,
derives the copied name pointer from the counted directory length instead of
`wcslen(path)`, rejects `target_name` backslashes through a counted scan, and
frees `path` before returning on malformed target names.

## Acceptance Gate

`docs/plan/check-srev-035.py` validates the local schema, official references,
source guard order, counted-string helper, and cleanup branch.

Windows gate still needed: call `SbieApi_RenameFile` through a sandboxed process
for normal rename, odd byte length, embedded NUL, embedded backslash in
`target_name`, and stale/short `MaximumLength` cases.
