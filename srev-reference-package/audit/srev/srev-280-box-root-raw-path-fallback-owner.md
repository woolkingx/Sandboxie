# SREV-280: Box Root Raw Path Fallback Owner

| Field | Content |
|---|---|
| Stage | schema -> boundary -> verify |
| Input artifact | `Sandboxie/core/dll/file_init.c`, SREV-057, SREV-276, Microsoft file namespace, MS-DOS device namespace, and `QueryDosDevice` documentation |
| Output artifact | Source comment owner, draft-07 schema, checker, and ledger fragment |
| Owner | `File_Init` box-root raw-path fallback publication |
| Acceptance gate | Targeted checker validates official references, raw-root fallback publication shape, SREV-057/SREV-276 adjacency, stale source wording removal, and ledger fragment |

## Data

`File_Init` first initializes `Dll_BoxFileDosPath` by copying
`Dll_BoxFilePath` and passing that copy through `SbieDll_TranslateNtToDosPath`.
If that route cannot produce a caller-visible DOS presentation, it queries the
driver-published raw root:

```text
SbieApi_QueryProcessInfoStr(0, 'root', NULL, &BoxFileRawPathLen)
BoxFileRawPathLen >= sizeof(WCHAR) && BoxFileRawPathLen <= 0xFFFF
Dll_AllocTemp(BoxFileRawPathLen)
SbieApi_QueryProcessInfoStr(0, 'root', BoxFileRawPath, &BoxFileRawPathLen)
*BoxFileRawPath
Dll_BoxFileRawPath = BoxFileRawPath
Dll_BoxFileRawPathLen = wcslen(Dll_BoxFileRawPath)
Dll_BoxFileDosPath = Dll_Alloc(BoxFileRawPathLen)
SbieDll_TranslateNtToDosPath(Dll_BoxFileDosPath)
Dll_BoxFileDosPathLen = wcslen(Dll_BoxFileDosPath)
```

SREV-057 owns the allocation, byte-capacity, and global-publication gates for
this block. SREV-276 owns the namespace translator. SREV-280 owns the comment
and topology classification of this fallback as an initialization-time
publication path, not a generic namespace conversion policy.

## Official Shape

Microsoft documents Windows paths as namespace-specific strings. Win32 file
paths, Win32 device paths, and NT object-manager paths are different
presentations over files, devices, volumes, and symbolic links.

Microsoft documents MS-DOS device names as junctions in the object namespace.
`QueryDosDevice` queries those junctions and explains that MS-DOS path
conversion uses them to map drive letters and DOS devices.

Microsoft documents local and global MS-DOS device namespaces. A DOS device
name may be visible only in a logon-session-local DosDevices context, while
system threads and LocalSystem run in the global DosDevices context.

Official references:

- `https://learn.microsoft.com/en-us/windows/win32/fileio/naming-a-file`
- `https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-querydosdevicea`
- `https://learn.microsoft.com/en-us/windows/win32/fileio/defining-an-ms-dos-device-name`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/kernel/local-and-global-ms-dos-device-names`

## Schema

Local schema:

```text
docs/plan/srev-280-box-root-raw-path-fallback-owner.schema.json
```

Contract id:

```text
BOX_ROOT_RAW_PATH_FALLBACK_OWNER
```

## Boundary

```text
driver-published raw box root
  -> File_Init local staging
  -> raw-root global publication
  -> same NT-to-DOS translator used by normal box root
  -> caller-visible DOS box root length publication
```

The fallback belongs to box-root initialization. It may query the raw root
already published by the driver and may run the existing translator over that
raw root. It does not own arbitrary NT-device to Win32-device conversion; that
boundary remains with SREV-276.

## Topology

```text
Dll_BoxFilePath
  -> copy into Dll_BoxFileDosPath allocation
  -> SbieDll_TranslateNtToDosPath
  -> publish Dll_BoxFileDosPathLen

translation miss
  -> query raw root byte capacity from driver
  -> local temp raw-root buffer
  -> second query + non-empty proof
  -> publish Dll_BoxFileRawPath + Dll_BoxFileRawPathLen
  -> copy raw root into Dll_BoxFileDosPath allocation
  -> SbieDll_TranslateNtToDosPath
  -> publish Dll_BoxFileDosPathLen only if translation succeeded
```

## Logic Risk

The old source comment called this block a workaround and pointed only at the
translator. That wording hid the owner boundary. The raw-root fallback is a
legitimate box-root publication route for roots whose normal NT presentation
does not map directly to the caller's DOS namespace. Treating it as a generic
translator concern can push future edits toward the wrong owner: enabling broad
device-name rewriting in `SbieDll_TranslateNtToDosPath` instead of preserving a
bounded raw-root fallback in `File_Init`.

## Fix

Comment-only source clarification. The source now names SREV-280 and states
that if the normal box root lacks a caller-visible DOS presentation, `File_Init`
queries the driver-published raw root and runs the same namespace translator
before publishing lengths. No behavior changed.

## Acceptance Gate

`docs/plan/check-srev-280.py` validates the draft-07 schema, official
references, `file_init.c` direct and raw-root fallback shape, raw-root query
and publication gates inherited from SREV-057, namespace translator adjacency
from SREV-276, stale source wording removal, and ledger fragment.

Runtime gate: Windows box-root matrix covering ordinary drive-letter roots,
reparse or mount-point roots whose target device lacks a caller-visible DOS
presentation, local/global DosDevices visibility, raw-query failure, empty
raw-root response, and fallback allocation failure.
