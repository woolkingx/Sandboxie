# SREV-273: File Final Path Volume-Name Owner

| Field | Content |
|---|---|
| Stage | schema -> topology -> verify |
| Input artifact | `Sandboxie/core/dll/file.c`, SREV-143, SREV-223, SREV-271, Microsoft `GetFinalPathNameByHandleW`, volume naming, and mounted-folder documentation |
| Output artifact | Source comment owner, draft-07 schema, checker, and ledger fragment |
| Owner | `File_GetFinalPathNameByHandleW_2` path-presentation normalization |
| Acceptance gate | Targeted checker validates official references, mounted-folder volume identity topology, stale comment removal, SREV adjacency, and ledger fragment |

## Data

`File_GetFinalPathNameByHandleW_2` receives a Sandboxie true path and
`dwFlags`, masks the volume-name flags to `VOLUME_NAME_GUID`,
`VOLUME_NAME_NT`, and `VOLUME_NAME_NONE`, rejects incompatible flag
combinations, special-cases MUP/network paths, delegates GUID output to
`File_GetFinalPathNameByHandleW_3`, and otherwise builds a DOS, NT, or no-volume
final path.

When `File_FindPermLinksForMatchPath(TruePath, TruePath_len)` finds a permanent
link, the code distinguishes two caller-visible volume identities:

- `VOLUME_NAME_NT` / `VOLUME_NAME_NONE` call
  `File_FixPermLinksForMatchPath(TruePath)`, update `TruePath` to the target
  device path, and compute `suffix = TruePath + file_link->src_len`.
- `VOLUME_NAME_DOS` keeps a drive-letter presentation. If the mounted-location
  path has no direct drive entry, it falls back to `file_link->src`, keeps
  `suffix2 = TruePath + file_link->dst_len`, and appends the mounted-folder
  suffix after the drive-root suffix.

## Official Shape

Microsoft documents `GetFinalPathNameByHandleW` as returning the final path of
a file handle, with volume-name flags selecting the returned volume identity:
`VOLUME_NAME_DOS` returns a drive-letter path, `VOLUME_NAME_GUID` returns a
volume GUID path, `VOLUME_NAME_NONE` returns no drive information, and
`VOLUME_NAME_NT` returns the NT device object path.

Microsoft documents mounted folders as an association between a volume and a
directory on another volume. Applications can access the target volume either by
the mounted-folder path or by a drive letter, and generally only need the
complete mounted-folder path to locate a file.

Microsoft documents volume naming as supporting drive-letter paths, volume GUID
paths, and volume mount points. Mounted-folder functions such as
`GetVolumeNameForVolumeMountPoint` retrieve the volume GUID path associated with
a drive letter, volume GUID path, or mounted folder.

Official references:

- `https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-getfinalpathnamebyhandlew`
- `https://learn.microsoft.com/en-us/windows/desktop/FileIO/volume-mount-points`
- `https://learn.microsoft.com/en-us/windows/win32/fileio/naming-a-volume`
- `https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-getvolumenameforvolumemountpointa`

## Boundary

The boundary is path-presentation only:

```text
open file handle
  -> Sandboxie true NT path
  -> File_GetFinalPathNameByHandleW_2(dwFlags)
  -> caller-visible final path string
```

The function does not own permanent-link discovery itself. SREV-143 owns the
permanent-link and GUID metadata. SREV-223 owns final-path returned-length
handling in the service `IsHostPath` breakout gate. SREV-271 owns
`NtQueryInformationFile(FileNameInformation)` root-relative output. This SREV
only names the `GetFinalPathNameByHandleW` volume-name presentation contract for
the DLL hook.

## Topology

```text
TruePath
  -> MUP network path
      -> VOLUME_NAME_GUID rejected
      -> VOLUME_NAME_NT keeps NT MUP identity
      -> VOLUME_NAME_NONE/DOS maps to UNC suffix
  -> VOLUME_NAME_GUID
      -> File_GetFinalPathNameByHandleW_3
  -> permanent-link match
      -> NT/NONE uses target device identity via File_FixPermLinksForMatchPath
      -> DOS uses mounted-location drive identity plus mounted-folder suffix
  -> ordinary local volume
      -> File_GetDriveForPath
      -> NT/NONE/DOS string construction
```

## Logic Risk

The old comment described example device paths but did not name the API owner:
the caller-visible result is selected by `GetFinalPathNameByHandleW` volume-name
flags. Future edits could incorrectly treat mounted-folder conversion as a raw
string cleanup and collapse the distinction between target-device identity
(`VOLUME_NAME_NT` / `VOLUME_NAME_NONE`) and mounted-location drive identity
(`VOLUME_NAME_DOS`).

## Fix

Comment-only source clarification. The mounted-folder block now names SREV-273
and states that `GetFinalPathNameByHandleW` volume-name flags select the
caller-visible identity: target device for NT/NONE output and mounted-location
drive for DOS output. No behavior changed.

## Acceptance Gate

`docs/plan/check-srev-273.py` validates the draft-07 schema, official
references, source comment owner, mounted-folder permanent-link branch, NT/NONE
target-device route, DOS mounted-location drive route, SREV-143/SREV-223/SREV-271
adjacency, stale example-path comment removal, and ledger fragment.

Runtime gate: Windows mounted-folder matrix for
`GetFinalPathNameByHandleW(VOLUME_NAME_DOS)`,
`GetFinalPathNameByHandleW(VOLUME_NAME_NT)`,
`GetFinalPathNameByHandleW(VOLUME_NAME_NONE)`, and
`GetFinalPathNameByHandleW(VOLUME_NAME_GUID)`, covering drive-letter,
mounted-folder, no-drive-letter, volume-GUID, and UNC/MUP inputs.
