# SREV-271: FileNameInformation Volume Relative Owner

## Stage Gate

| Field | Value |
|---|---|
| Stage | schema -> topology -> logic -> action -> verify |
| Input artifact | `Sandboxie/core/dll/file.c`, SREV-143, Microsoft `NtQueryInformationFile`, `FILE_NAME_INFORMATION`, volume naming, and mounted-folder documentation |
| Output artifact | `docs/plan/srev-271-file-name-info-volume-relative-owner.schema.json`, `docs/plan/check-srev-271.py`, `docs/plan/check-srev-271.sh`, ledger fragment, comment-only source clarification |
| Owner | `File_NtQueryInformationFile` `FileNameInformation` path-presentation normalization |
| Acceptance gate | targeted source checker, core coverage, and diff checkpoint |

## Evidence

`File_NtQueryInformationFile` intercepts `FileNameInformation` and writes a
`FILE_NAME_INFORMATION`-compatible output buffer. The local hook first asks
`File_GetName` for the true path, then normalizes Sandboxie path topology back
to the name shape callers expect.

Two covered comment-risk sites were left as symptom wording:

- mounted-folder paths could arrive as the mount location, such as a path under
  one `\Device\HarddiskVolume...` prefix that represents another target volume;
- when `SbieDll_TranslateNtToDosPath` fails, a `todo: fix-me this is not
  elegant` branch strips a known volume GUID/device prefix with
  `File_GetGuidForPath`.

SREV-143 already owns the lower-level permanent-link and volume-GUID metadata
shape. This SREV records the consumer boundary in `file.c`: the
`FileNameInformation` caller receives a root-relative file name, not the
internal mount-location or GUID prefix.

## Official Shape

Microsoft documents `NtQueryInformationFile(FileNameInformation)` as returning a
`FILE_NAME_INFORMATION` structure. The returned name can be a full path or a
relative path depending on how the file was opened and privilege state. When a
full path is returned, it begins with one backslash; a `C:\dir\file` path appears
as `\dir\file`, and a UNC path appears as `\server\share\dir\file`.

Microsoft documents `FILE_NAME_INFORMATION.FileNameLength` as a byte count and
`FileName` as the first character of the returned file-name string.

Microsoft documents volume GUID paths and mounted folders as alternate volume
identities. A volume may have no drive letter, and a mounted folder can expose a
target volume through a directory on another volume.

```text
https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/nf-ntifs-ntqueryinformationfile
https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/ns-ntifs-_file_name_information
https://learn.microsoft.com/en-us/windows/win32/fileio/naming-a-volume
https://learn.microsoft.com/en-us/windows/win32/fileio/volume-mount-points
```

## Data

`File_NtQueryInformationFile`, `FileNameInformation`,
`FILE_NAME_INFORMATION.FileNameLength`, `File_GetName`, `TruePath`,
`File_FindPermLinksForMatchPath`, `FILE_LINK.dst_len`, `File_Mup`,
`SbieDll_TranslateNtToDosPath`, `File_GetGuidForPath`, `FILE_GUID.len`,
`File_DrivesAndLinks_CritSec`, and the final returned name buffer.

## Schema

`FILE_NAME_INFO_VOLUME_RELATIVE_OWNER` says:

- `File_NtQueryInformationFile` owns the presentation shape for intercepted
  `FileNameInformation` output;
- returned disk names are root-relative to the caller-visible volume identity,
  not raw Sandboxie link storage paths;
- mounted-folder matches from `File_FindPermLinksForMatchPath` must strip the
  destination prefix and release `File_DrivesAndLinks_CritSec`;
- if NT-to-DOS translation fails but `File_GetGuidForPath` finds a known volume
  identity, the returned name strips the GUID/device prefix and releases the
  same lock;
- this SREV changes comments and proof only; SREV-143 still owns permanent-link
  and GUID metadata correctness.

## Topology

```text
open file handle
  -> File_NtQueryInformationFile(FileNameInformation)
  -> File_GetName true path
  -> mounted-folder / MUP / DOS-drive / GUID classification
  -> root-relative returned FileNameInformation payload
```

Mounted-folder consumer flow:

```text
TruePath at mounted-folder storage prefix
  -> File_FindPermLinksForMatchPath
  -> strip file_link->dst_len
  -> release File_DrivesAndLinks_CritSec
  -> return target-volume relative suffix
```

GUID fallback consumer flow:

```text
SbieDll_TranslateNtToDosPath fails
  -> File_GetGuidForPath(TruePath)
  -> strip guid->len
  -> release File_DrivesAndLinks_CritSec
  -> return volume-relative suffix
```

## Logic Risk

The source was doing the right style of topology conversion but described it as
symptom prose and a `todo`. That invites future changes to treat this as a
formatting cleanup instead of a volume-identity boundary. Removing either strip
without reproving mounted-folder, no-drive-letter volume, and GUID paths would
return an internal mount location instead of the caller-visible relative name.

## Fix

Comment-only source clarification. The mounted-folder block now names SREV-271
and says the returned name is root-relative to the target volume. The GUID
fallback block no longer carries `todo: fix-me`; it says the branch handles NT
paths with no DOS drive presentation by stripping a known volume identity prefix.
No behavior changed.

## Acceptance Gate

`docs/plan/check-srev-271.py` validates the draft-07 schema, official references,
SREV-143 adjacency, source comment owners, mounted-folder prefix stripping,
GUID fallback prefix stripping, `File_DrivesAndLinks_CritSec` release paths,
removal of stale `todo: fix-me` wording from this block, and the ledger
fragment.

Runtime gate: Windows mounted-folder volume, no-drive-letter volume, volume GUID
path, ordinary drive-letter path, and UNC/MUP matrix for
`NtQueryInformationFile(FileNameInformation)`, proving returned names remain
root-relative where required and do not leak Sandboxie internal mount-location
prefixes.
