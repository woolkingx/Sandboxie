# SREV-056: File Delete Path Tree Buffer Boundary

## Data

`Sandboxie/core/dll/file_del.c` serializes the deleted-file path tree to the
box data file. `File_SavePathTree_internal` allocates one fixed NT path buffer
and `File_SavePathNode_internal` recursively appends path components into it.

`File_TranslateNtToDosPathForDatFile` then converts each serialized NT path into
a DOS-style path. It also handles the source-admitted special case where a
nonexistent drive is stored as a fake tree entry such as:

```text
\C:\path
```

## Official Shape

Microsoft documents wide-character strings as `wchar_t[]` arrays terminated by
`L'\0'`:

```text
https://learn.microsoft.com/en-us/cpp/c-runtime-library/unicode-the-wide-character-set
```

Microsoft documents `wcschr` as operating on wide-character strings and finding
the first occurrence of a character:

```text
https://learn.microsoft.com/en-us/cpp/c-runtime-library/reference/strchr-wcschr-mbschr-mbschr-l
```

Microsoft documents `wmemmove` as moving wide characters and notes that the
destination buffer must be large enough:

```text
https://learn.microsoft.com/en-us/cpp/c-runtime-library/reference/memmove-wmemmove
```

## Schema

Local schema:

```text
docs/plan/srev-056-file-del-path-tree-buffer.schema.json
```

The path-tree serializer owns a fixed-capacity WCHAR buffer:

```text
capacity = 0x7FFF + 1 WCHARs
```

Every recursive append must leave room for the component and its terminating
NUL. Translation must receive a non-empty NUL-terminated input string and an
allocated output buffer before any wide-string operation.

## Topology

```text
PATH_NODE tree -> fixed WCHAR path buffer -> DAT-file path translation -> NtWriteFile
```

The path tree owns component names. The serializer owns the temporary full-path
buffer. The translator owns the allocated DOS path returned to the writer.

## Logic Risk

Before this patch, the recursive serializer appended `\` and child names without
carrying the buffer capacity. A deep or malformed tree could write past the
`0x7FFF + 1` allocation. The same save path also used the allocation result
without checking for failure, and the translator dereferenced its allocation and
searched from `DosPath + 1` without rejecting null or empty input first.

## Fix

`File_SavePathNode_internal` now carries `PathCapacity`, returns before appending
when the slash would exceed capacity, and skips any child component that cannot
fit with its terminator. `File_SavePathTree_internal` checks the path-buffer
allocation and closes the output file on allocation failure. The translator now
rejects null or empty `NtPath` and returns `NULL` when its output allocation
fails.

## Acceptance Gate

`docs/plan/check-srev-056.py` validates the draft-07 schema, official reference
links, recursive capacity propagation, slash/component fit gates, allocation
checks, null/empty translator guard, and ledger entry.

Windows gate: deleted-file path tree save should handle normal paths, fake
nonexistent-drive `\C:\...` paths, very deep trees, allocation failure, and empty
or malformed translation input without buffer overrun or null dereference.
