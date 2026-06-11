# SREV-057: Box Root DOS Path Publication Boundary

## Data

`Sandboxie/core/dll/file_init.c` initializes `Dll_BoxFileDosPath`, the DOS-path
projection of `Dll_BoxFilePath`. If the NT-to-DOS translation fails because the
box root is redirected through a reparse point to a target device without a
drive letter, it queries the raw root path through `SbieApi_QueryProcessInfoStr`
and tries the translation again.

The owned state is:

```text
Dll_BoxFilePath
Dll_BoxFilePathLen
Dll_BoxFileDosPath
Dll_BoxFileDosPathLen
Dll_BoxFileRawPath
Dll_BoxFileRawPathLen
```

## Official Shape

Microsoft documents `UNICODE_STRING` as carrying byte lengths and a wide-string
buffer:

```text
https://learn.microsoft.com/en-us/windows/win32/api/ntdef/ns-ntdef-_unicode_string
```

Microsoft documents `wcscpy` as copying a null-terminated wide string into the
destination and not checking destination size:

```text
https://learn.microsoft.com/en-us/cpp/c-runtime-library/reference/strcpy-wcscpy-mbscpy
```

Microsoft documents `NT_SUCCESS` as the macro for testing NTSTATUS results:

```text
https://learn.microsoft.com/en-us/windows-hardware/drivers/kernel/using-ntstatus-values
```

## Schema

Local schema:

```text
docs/plan/srev-057-file-init-box-root-path.schema.json
```

Local wire shape:

```text
SbieApi_QueryProcessInfoStr(ProcessId, info_type, out_str, inout_str_len)
```

When `out_str` is non-null, `SbieApi_QueryProcessInfoStr` builds a
`UNICODE_STRING64` with:

```text
Length = 0
MaximumLength = (USHORT)*inout_str_len
Buffer = out_str
```

So `BoxFileRawPathLen` is a byte capacity for the raw-root output buffer, not a
WCHAR count. Because the local API truncates that capacity into a `USHORT`
`MaximumLength`, the fallback accepts only `sizeof(WCHAR) <= BoxFileRawPathLen <=
0xFFFF`. The fallback must stage the raw output locally and publish the global
pointer only after `NT_SUCCESS` and non-empty string proof.

Global root-path state is published only when the source string and allocation
are both valid:

```text
translated DOS path -> Dll_BoxFileDosPath + Dll_BoxFileDosPathLen
raw root path       -> Dll_BoxFileRawPath + Dll_BoxFileRawPathLen
```

An allocation failure or failed raw-root query leaves the corresponding global
pointer null and length zero.

## Topology

```text
box NT root -> direct NT-to-DOS translation -> DOS path global
          \-> raw root query fallback -> raw path global -> DOS path global
```

The file-init path owns publication of these globals. Consumers use the length
fields as gates before prefix matching or path rewriting.
SREV-264 later classified `File_AltBoxPath` as a legacy mount-point prefix
fallback in `File_FindBoxPrefix`; removing it requires re-proving this
raw-root/mount-point matrix on Windows.

## Logic Risk

Before this patch, `Dll_BoxFileDosPath` allocations were dereferenced by
`wcscpy` without checking for allocation failure. The raw-root fallback assigned
`Dll_BoxFileRawPath` before proving that the second `SbieApi_QueryProcessInfoStr`
call succeeded and returned a non-empty string. A non-null raw pointer with
`Dll_BoxFileRawPathLen == 0` could later behave like an empty prefix gate.

## Fix

The direct DOS path is copied and translated only when its allocation succeeds.
The raw-root fallback now queries into a local temporary pointer, publishes
`Dll_BoxFileRawPath` only after the second query succeeds and returns a non-empty
string, checks the fallback DOS-path allocation, and only then copies and
translates the raw path. Failed paths leave global pointers null and lengths
zero.

## Acceptance Gate

`docs/plan/check-srev-057.py` validates the draft-07 schema, official reference
links, allocation gates before `wcscpy`, local raw-path staging before global
publication, non-empty raw-path gate, fallback allocation gate,
`File_AltBoxPath` legacy-fallback adjacency, and ledger entry.

Windows gate: normal box-root translation, reparse/no-drive raw-root fallback,
direct allocation failure, raw-query failure, empty raw-root response, and
fallback allocation failure should not crash and should not publish a non-null
zero-length raw root.
