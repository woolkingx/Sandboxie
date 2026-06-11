# SREV-277: FilePaths Unknown-Drive Sentinel

| Field | Content |
|---|---|
| Stage | data -> schema -> verify |
| Input artifact | `Sandboxie/core/dll/file_del.c`, Microsoft path namespace and MS-DOS device mapping documentation |
| Output artifact | Source comment owner, draft-07 schema, checker, and ledger fragment |
| Owner | `File_TranslateNtToDosPathForDatFile` FilePaths.dat save-time path projection |
| Acceptance gate | Targeted checker validates official references, load/save round-trip topology, unknown-drive sentinel stripping, stale hack wording removal, and ledger fragment |

## Data

`Sandboxie/core/dll/file_del.c` persists deleted and relocated path state in
`FilePaths.dat`.

The round trip has two projection functions:

- `File_TranslateDosToNtPathForDatFile` runs while loading the file. If a
  persisted drive-letter path cannot be mapped through `File_GetDriveForLetter`,
  it leaves the DOS path in the in-memory tree instead of dropping the entry.
- `File_TranslateNtToDosPathForDatFile` runs while saving the tree. It converts
  known NT paths to DOS/UNC forms, and it has a special case for the preserved
  unknown-drive sentinel form `L"\\C:\\path"`.

The sentinel is deliberately not a normal NT path. It is a data-preservation
shape for a drive-letter entry whose current NT target is unknown.

## Official Shape

Microsoft documents drive letters and MS-DOS device names as namespace junctions
that map DOS names to target paths. `QueryDosDevice` can query those junctions.
Microsoft also documents local and global MS-DOS device namespaces, so a drive
letter may be unavailable in the current context even though a persisted
drive-letter path still matters.

Official references:

- `https://learn.microsoft.com/en-us/windows/win32/fileio/naming-a-file`
- `https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-querydosdevicea`
- `https://learn.microsoft.com/en-us/windows/win32/fileio/defining-an-ms-dos-device-name`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/kernel/local-and-global-ms-dos-device-names`

## Boundary

```text
FilePaths.dat line
  -> load-time DOS-to-NT projection
  -> in-memory PATH_NODE tree
  -> save-time NT-to-DOS projection
  -> FilePaths.dat line
```

The owner is the persistence projection, not live file access. If a drive-letter
mapping is unknown, the correct behavior is to preserve the entry in a reversible
sentinel shape rather than silently dropping it or inventing an NT device path.

## Topology

```text
load C:\path
  -> File_GetDriveForLetter('C') succeeds
      -> store true NT path
  -> File_GetDriveForLetter('C') fails
      -> store preserved DOS sentinel as \C:\path

save \C:\path sentinel
  -> detect colon before first path separator
  -> strip one leading backslash
  -> write C:\path

save known NT path
  -> MUP / drive / UNC mapping
  -> write caller-visible DOS/UNC path
```

## Logic Risk

The old `Hack Hack` wording hid a legitimate data-shape invariant. Removing the
branch would lose deletion/relocation entries for currently unavailable drives.
Broadening it would corrupt real NT paths that merely contain a colon in a later
component. The sentinel strip is legal only when the colon immediately precedes
the first path separator or terminator after the leading backslash.

## Fix

Comment-only source clarification. The comment now names SREV-277 and describes
the leading-backslash unknown-drive sentinel used to preserve `FilePaths.dat`
entries across missing drive mappings. No behavior changed.

## Acceptance Gate

`docs/plan/check-srev-277.py` validates the draft-07 schema, official
references, `File_TranslateDosToNtPathForDatFile` load-time drive mapping,
`File_TranslateNtToDosPathForDatFile` save-time sentinel strip, stale hack
wording removal, and ledger fragment.

Runtime gate: Windows FilePaths.dat round trip with an available drive letter,
an unavailable/removable drive-letter path, UNC/MUP path, volume serial suffix
mode, and reappearance of the drive mapping after reload.
