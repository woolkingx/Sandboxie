# SREV-012 Reparse Buffer Shape

Status: source-level spec before patch.

## Official Shape

Microsoft documents `FSCTL_SET_REPARSE_POINT` as taking a caller-allocated
`REPARSE_DATA_BUFFER` or `REPARSE_GUID_DATA_BUFFER`. The input length must be at
least the corresponding header plus user data and no larger than the maximum
reparse buffer size. Invalid parameters can return
`STATUS_IO_REPARSE_DATA_INVALID`.

Microsoft also documents `FsRtlValidateReparsePointBuffer` as the kernel helper
that verifies buffer length, header/data-length consistency, and tag validity.
Sandboxie DLL code cannot call the kernel helper, but any pre-native parsing
must not read fields that such validation would reject.

For Microsoft symlink and mount-point tags:

- `SubstituteNameOffset` and `PrintNameOffset` are byte offsets from byte 0 of
  `PathBuffer`.
- `SubstituteNameLength` and `PrintNameLength` are byte lengths.
- The strings can appear in any order inside `PathBuffer`.
- The documented lengths do not include a terminating Unicode null if one is
  present.
- Symlink reparse data length covers the path buffer plus 12 bytes after the
  common header. Mount-point reparse data length covers the path buffer plus 8
  bytes after the common header.

Sources:

- https://learn.microsoft.com/en-us/windows-hardware/drivers/ifs/fsctl-set-reparse-point
- https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/ns-ntifs-_reparse_data_buffer
- https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/nf-ntifs-fsrtlvalidatereparsepointbuffer
- https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-fscc/b41f1cbf-10df-4a47-98d4-1c52a833d913
- https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-fscc/ca069dad-ed16-42aa-b057-b6b207f447cc

## Local Risk

`File_SetReparsePoint` reads `SubstituteNameOffset`, `SubstituteNameLength`,
`PrintNameOffset`, and `PrintNameLength`, then computes pointers into
`PathBuffer` before proving those ranges fit in the caller's `DataLen`.

It also copies `PrintNameLength + sizeof(WCHAR)` from the caller buffer even
though the official length contract does not guarantee an in-buffer terminator.

## Acceptance Gate

- `DataLen` must cover the fixed tag-specific fields before those fields are
  trusted.
- `ReparseDataLength` must fit inside `DataLen`.
- Each substitute/print name range must be even-byte aligned and fully inside
  `PathBuffer`.
- The old print name copy must copy only `PrintNameLength` bytes from the caller
  and synthesize the output terminator.
