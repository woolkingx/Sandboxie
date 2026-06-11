# SREV-155: File Reparse Cache Counted Object Name

## Stage Gate

| Field | Content |
|---|---|
| Stage | schema -> boundary -> topology -> logic -> action -> verify |
| Input artifact | `Sandboxie/core/drv/file_xlat.c`, KPATH-002 reparse translation runtime plan, Microsoft object-name / Unicode-string references |
| Output artifact | Source-level counted object-name hardening, draft-07 schema, checker, ledger fragment |
| Owner | `Sandboxie/core/drv/file_xlat.c` owns reparse-point translation cache entries |
| Acceptance gate | Source proves `OBJECT_NAME_INFORMATION.Name.Length` drives destination path length and no `wcslen(Name->Name.Buffer)` C-string scan remains in `file_xlat.c` |

## Data

`File_TranslateReparsePoints_3` opens the candidate directory path, references
the resulting `FILE_OBJECT`, calls `Obj_GetName`, and caches the returned
object name as `CACHE_PATH::dst`. Before this SREV, the cache destination
length came from:

```c
WCHAR *path3 = Name->Name.Buffer;
dst_len = wcslen(path3);
```

The later cache allocation and copy used that computed `dst_len` to copy
`Name->Name.Buffer` into a driver-pool cache entry.

## Official Shape

Microsoft documents `ObQueryNameString` as returning
`OBJECT_NAME_INFORMATION`, whose `Name` member is a `UNICODE_STRING`. Microsoft
documents `UNICODE_STRING.Length` as the byte length of the string stored in
`Buffer`, and if a string is null-terminated, `Length` does not include the
trailing null character.

`ObQueryNameString` remarks say successful named-object output has a
null-terminated buffer, but the authoritative string extent is still the
`UNICODE_STRING.Length` byte count. `file_xlat.c` is not just logging the name;
it uses the length as a cache allocation and copy boundary, so it should use the
counted extent instead of re-scanning for a terminator.

Official references:

- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/nf-ntifs-obquerynamestring`
- `https://learn.microsoft.com/en-us/windows/win32/api/ntdef/ns-ntdef-_unicode_string`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-rtlinitunicodestring`

## Topology

Legal flow:

```text
ZwCreateFile(directory path)
  -> ObReferenceObjectByHandle(FILE_OBJECT)
  -> Obj_GetName / ObQueryNameString
  -> OBJECT_NAME_INFORMATION.Name.Length counted extent
  -> trim trailing backslashes within counted extent
  -> CACHE_PATH::dst allocation and copy
```

KPATH-002 remains a separate topology:

```text
File_ReparsePointsBusy
  -> global wait around File_TranslateReparsePoints_3 I/O
  -> Windows runtime timing / timeout design gate
```

This SREV does not change that wait topology.

## Logic Risk

The old code crossed from counted kernel object-name data to a C-string scan
before allocating and copying the cache destination. Even if `ObQueryNameString`
normally includes a null terminator, the local owner already has the counted
length and should not make allocation/copy decisions from a terminator search.

This is source-level schema hardening, not a complete reparse translation
runtime fix. KPATH-002 still owns bounded waiting, negative-cache behavior, and
slow/offline path runtime proof.

## Fix

`File_TranslateReparsePoints_3` now requires `Name->Name.Buffer` and an even
`Name->Name.Length`, derives `dst_len` from
`Name->Name.Length / sizeof(WCHAR)`, and trims trailing backslashes by indexing
within `Name->Name.Buffer` under that counted length. The cache allocation,
copy, pass behavior, `ZwCreateFile` flags, `Obj_GetName` ownership, and
`File_ReparsePointsBusy` wait topology are otherwise unchanged.

## Acceptance Gate

`docs/plan/check-srev-155.py` validates the draft-07 schema, official
references, counted `OBJECT_NAME_INFORMATION.Name` use, removal of the
`wcslen(Name->Name.Buffer)` destination-length scan, preservation of
`ZwCreateFile` / `Obj_GetName` / cache-copy topology, unchanged KPATH-002
runtime design boundary, and ledger fragment.

Runtime/build gate: Windows driver build for `file_xlat.c`; reparse/junction
translation smoke proving ordinary object names still cache and rewrite;
instrumented object-name cases with counted length and terminator variance;
slow/offline reparse path observation for KPATH-002; Driver Verifier and HVCI
where supported.
