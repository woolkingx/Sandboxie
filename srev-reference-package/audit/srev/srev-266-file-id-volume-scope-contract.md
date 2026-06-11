# SREV-266: File ID Volume Scope Contract

## Stage Gate

| Field | Value |
|---|---|
| Stage | schema -> topology -> logic -> action -> verify |
| Input artifact | `Sandboxie/core/dll/file.c`, Microsoft `FILE_INTERNAL_INFORMATION` and `NtCreateFile` documentation |
| Output artifact | `docs/plan/srev-266-file-id-volume-scope-contract.schema.json`, `docs/plan/check-srev-266.py`, `docs/plan/check-srev-266.sh`, ledger fragment, comment-only source clarification |
| Owner | `File_GetName_FromFileId` and file-information FileId scramble/unscramble pair |
| Acceptance gate | targeted source checker, core coverage, and diff checkpoint |

## Evidence

`File_GetName_FromFileId` handles `FILE_OPEN_BY_FILE_ID` callers whose
`ObjectAttributes->RootDirectory` may be a sandbox path such as
`D:\sandbox\drive\C` instead of the real `C:` parent. Later,
`File_NtQueryInformationFile` scrambles FileId values returned from boxed files
so a caller cannot accidentally reuse a sandbox-volume FileId as though it were
a real-volume FileId.

The old comments described this as a workaround for C: and D: drives having the
same FileId. That captured the symptom, but not the schema: file IDs are scoped
to their file system/volume, and `FILE_OPEN_BY_FILE_ID` consumes a binary
8-byte or 16-byte reference, not a normal Unicode file name.

## Official Shape

Microsoft documents `FILE_INTERNAL_INFORMATION.IndexNumber` as an 8-byte file
reference number assigned by the file system. The same value is exposed as the
`FileId` member of `FILE_ID_BOTH_DIR_INFORMATION` and
`FILE_ID_FULL_DIR_INFORMATION`, and file IDs are guaranteed unique only within a
static file system.

Microsoft documents `NtCreateFile(FILE_OPEN_BY_FILE_ID)` as opening by a binary
8-byte or 16-byte file reference/object ID depending on the file system, and
warns that the name field partly contains a binary blob rather than a valid,
null-terminated Unicode string.

```text
https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/ns-ntifs-_file_internal_information
https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/nf-ntifs-ntcreatefile
```

## Data

`File_GetName_FromFileId`, `ObjectAttributes->RootDirectory`,
`ObjectAttributes->ObjectName`, `FILE_OPEN_BY_FILE_ID`, `SbieDll_GetHandlePath`,
`FILE_INTERNAL_INFORMATION.IndexNumber`, `FILE_ALL_INFORMATION`, and the
FileId XOR scramble/unscramble pair.

## Schema

`FILE_ID_VOLUME_SCOPE_CONTRACT` says:

- file IDs are scoped to the file system/volume that assigned them;
- open-by-id object names are binary reference numbers, not Unicode path
  strings;
- boxed FileIds returned through file information paths are scrambled only so
  the paired `File_GetName_FromFileId` route can distinguish sandbox-volume IDs
  from real-volume IDs;
- `File_GetName_FromFileId` first tries a true parent directory for boxed roots,
  then falls back to the caller root and scrambled-ID retry;
- this SREV does not change XOR shape, query classes, access masks, share flags,
  or open-by-id policy.

## Topology

```text
boxed file information query
  -> sandbox-volume FileId scramble
  -> caller open-by-id request
  -> File_GetName_FromFileId
  -> true-parent retry for boxed roots
  -> caller-root retry
  -> unscrambled sandbox FileId retry
```

## Logic Risk

If the comments frame this as a generic drive-letter workaround, future changes
can attack the wrong owner: drive-letter syntax instead of file-system-scoped
identity. The legal invariant is volume scope plus binary open-by-id shape. Any
behavioral change must prove both real-root and sandbox-root routes.

## Fix

Comment-only source clarification. The source now names SREV-266 and describes
the file-system-scoped FileId contract at both the open-by-id route and the
file-information scramble route. No behavior changed.

## Acceptance Gate

`docs/plan/check-srev-266.py` validates the draft-07 schema, official references,
source comment owner, open-by-id input gates, true-parent retry, caller-root
retry, XOR scramble/unscramble pair, and the ledger fragment.

Runtime gate: Windows file-id matrix with boxed and unboxed roots on distinct
volumes, same numeric FileId collision simulation where possible, and
FileInternalInformation/FileAllInformation callers followed by open-by-id retry.
