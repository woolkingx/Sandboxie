# SREV-143: File Link Prefix And GUID Translation

## Stage Gate

| Field | Value |
|---|---|
| Stage | action |
| Input artifact | `Sandboxie/core/dll/file_link.c`, `Sandboxie/core/dll/file_init.c`, `Sandboxie/core/dll/file_misc.c`, Microsoft path namespace, volume GUID path, `GetVolumeNameForVolumeMountPointW`, and `REPARSE_DATA_BUFFER` references |
| Output artifact | `docs/plan/srev-143-file-link-prefix-guid-translation.schema.json`, `docs/plan/check-srev-143.py`, `docs/plan/check-srev-143.sh`, ledger fragment |
| Owner | DLL-side file link prefix matching and volume GUID target translation in `file_link.c` |
| Acceptance gate | source checker plus full SREV/KPATH/core coverage matrix; Windows runtime proof remains required for permanent links and symlink-to-volume-GUID targets |

## Evidence

`Sandboxie/core/dll/file_link.c` was the top unnamed reviewable core file after
SREV-142. It owns DLL-side drive/link metadata, temporary links, permanent link
translation, volume GUID links, and symlink/junction target translation before
file paths cross into later open/copy logic.

Two local defects shared the same path-identity boundary:

- `File_TranslateGuidToNtPath2` looked up a known `\\??\\Volume{...}` link and
  called `File_ConcatPath2`, but discarded the returned allocated path. The
  function therefore returned `NULL` even when the volume GUID was known, and
  the allocated concatenation was leaked.
- `File_GetDriveAndLinkForPath` matched a permanent-link source prefix but
  checked `Path[PathLen]` for the separator/NUL boundary. The common caller in
  `file_misc.c` passes `wcslen(path)`, so `Path[PathLen]` is normally the final
  NUL and does not prove that the matched prefix is a complete path component.
  The local precedent in `File_GetDriveForPath`, `File_FixPermLinksForTempLink`,
  and `File_FindPermLinksForMatchPath` checks the character immediately after
  the matched prefix.

Official references:

- https://learn.microsoft.com/en-us/windows/win32/fileio/naming-a-file
- https://learn.microsoft.com/en-us/windows/win32/fileio/naming-a-volume
- https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-getvolumenameforvolumemountpointw
- https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/ns-ntifs-_reparse_data_buffer

## Data

`FILE_LINK`, `FILE_GUID`, `File_PermLinks`, `File_GuidLinks`,
`File_DrivesAndLinks_CritSec`, `File_GetLinkForGuid`,
`File_TranslateGuidToNtPath2`, `File_TranslateGuidToNtPath`,
`File_ConcatPath2`, `File_AddTempLink`, `File_GetDriveAndLinkForPath`,
`File_GetDriveForPath`, `File_FixPermLinksForTempLink`,
`File_FindPermLinksForMatchPath`, `File_GetName`, `PathLen`, `src_len`,
`GuidPathLen`, `SubstituteNameBuffer`, and `REPARSE_DATA_BUFFER`.

## Schema

`FILE_LINK_PREFIX_GUID_TRANSLATION` says:

- `file_link.c` owns permanent-link prefix matching and volume GUID path
  translation inside the DLL path metadata lock.
- A permanent link source match is valid only when `PathLen >= src_len`, the
  prefix bytes match, and the character at `Path[src_len]` is either a
  backslash or NUL.
- `Path[PathLen]` is the end of the caller-supplied string when `PathLen` comes
  from `wcslen(path)`, so it cannot prove the prefix boundary.
- Known volume GUID targets in `\\??\\Volume{GUID}\\...` form must return the
  allocated `File_ConcatPath2(guid->path, guid->len, suffix, suffix_len)`
  result to the caller.
- The GUID lookup lock is released exactly once after a successful
  `File_GetLinkForGuid` lookup.
- `File_ConcatPath2` remains the owner-local path allocation helper and returns
  a NUL-terminated allocated string.
- Symlink/reparse target byte offsets remain interpreted as counted
  `REPARSE_DATA_BUFFER` data; this SREV only fixes the local GUID translation
  return value and permanent-link prefix boundary.

## Topology

Legal permanent-link match flow:

```text
File_GetName
  -> File_GetDriveAndLinkForPath(path, wcslen(path), FileLink)
  -> iterate File_PermLinks under File_DrivesAndLinks_CritSec
  -> require PathLen >= src_len
  -> require _wcsnicmp(Path, link->src, src_len) == 0
  -> require Path[src_len] is backslash or NUL
  -> return matching link plus drive under one remaining lock ownership
```

Legal volume GUID translation flow:

```text
File_AddTempLink
  -> absolute symlink target starts with \\??\\Volume{
  -> File_TranslateGuidToNtPath2
  -> File_GetLinkForGuid(&GuidPath[10]) returns FILE_GUID under lock
  -> NtPath = File_ConcatPath2(guid->path, guid->len, GuidPath + 48, GuidPathLen - 48)
  -> release File_DrivesAndLinks_CritSec
  -> caller owns returned allocated NT path or receives NULL on no match
```

## Logic Risk

Both defects affect path identity, not presentation. A prefix boundary checked
at `Path[PathLen]` can accept sibling path names that merely share the same
bytes as a permanent-link source prefix. A discarded `File_ConcatPath2` return
turns a known volume GUID link into an untranslated path and leaks the allocated
concatenation. The owner-local fix is to align the boundary check with the local
prefix-match precedent and to return the allocated GUID translation result.

This SREV does not change reparse buffer validation policy, drive discovery,
temporary link creation, WOW64 link exclusion, GUID storage format, or
`File_DrivesAndLinks_CritSec` ownership topology.

## Fix

`File_TranslateGuidToNtPath2` now assigns the `File_ConcatPath2` result to
`NtPath` before releasing the GUID/link metadata lock and returning to the
caller.

`File_GetDriveAndLinkForPath` now checks `Path[src_len]` for the
backslash-or-NUL boundary after a permanent-link source prefix match, matching
the existing local style in `File_FixPermLinksForTempLink` and
`File_FindPermLinksForMatchPath`.

## Acceptance Gate

`docs/plan/check-srev-143.py` validates the draft-07 schema, official reference
links, GUID translation assignment, absence of discarded GUID concatenation,
local `File_ConcatPath2` allocation shape, permanent-link prefix boundary at
`Path[src_len]`, absence of the stale `Path[PathLen]` boundary, local precedent
for prefix-boundary checks, the `wcslen(path)` call site, adjacent
reparse/GUID target flow evidence, and the ledger fragment.
`docs/plan/check-srev-143.sh` is the matrix wrapper.

Runtime/build gate: Windows DLL build; permanent-link sibling-prefix smoke
proving `src` does not match `srcSuffix` without a separator; permanent-link
exact-prefix and child-path smoke proving valid paths still translate; symlink
or junction target using `\\??\\Volume{GUID}\\...` proving known GUID targets
translate to the recorded NT path and do not return `NULL`; leak/handle
instrumentation proving no discarded `File_ConcatPath2` allocation remains on
the successful GUID branch.
