# SREV-001 Directory Information Buffer Shape

This note locks the official Windows shape before changing
`File_MergeDummy`.

## Official Shape

`FILE_ID_BOTH_DIR_INFORMATION` is a variable-size directory-enumeration record.
Its relevant fields are:

- `NextEntryOffset`: byte offset to the next record; zero means no following
  record.
- `FileNameLength`: length, in bytes, of the file name string.
- `FileName[1]`: first character of a variable-length file name payload,
  followed in memory by the remainder of the string.

Microsoft also specifies that the structure must be aligned on an 8-byte
boundary and that, when multiple records are present, each non-final
`NextEntryOffset` falls on an 8-byte boundary.

The MS-FSCC protocol view states the same shape more normatively: each record in
a multi-record buffer is aligned on an 8-byte boundary, alignment bytes should
be zero, and receivers use `NextEntryOffset` to find the next record.

Official references:

- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/ns-ntifs-_file_id_both_dir_information`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/nf-ntifs-ntquerydirectoryfile`
- `https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-fscc/1e144bff-c056-45aa-bd29-c13d214ee2ba`

## Local Shape

`Sandboxie/core/dll/file_dir.c` uses the same shape in two places:

- `File_MergeCache` reads real directory records from `NtQueryDirectoryFile`.
- `File_MergeDummy` fabricates records from path rules when rule specificity
  allows access to subpaths under an inaccessible parent.

The fabricated records are an internal staging buffer. They are converted into
`FILE_MERGE_CACHE_FILE` records before being returned to callers.

## Analysis

The pre-fix `File_MergeDummy` shape is invalid for two independent reasons:

- It appends variable-size records into a fixed `0x10000` `info_area` without
  tracking remaining capacity.
- It treats `FileNameLength` as a `WCHAR` index when writing a terminator:
  `FileName[FileNameLength]`, even though the field is a byte count.

The official schema does not require a trailing null in the directory entry.
Sandboxie's later cache conversion already uses `FileNameLength`, so a synthetic
record should not need a terminator at all.

The correct local transition is:

```text
path rule segment -> file-name byte length -> variable directory record
                  -> 8-byte aligned next offset -> cache record
```

The local invariant is:

```text
FIELD_OFFSET(FILE_ID_BOTH_DIR_INFORMATION, FileName) + FileNameLength
must fit in remaining info_area bytes before any write.
```

If the staging area is full, the safe transition is to stop appending more
synthetic records and return the complete records already staged. This mirrors
directory-enumeration fit semantics: only complete records may be returned.
No partial record should be written.
