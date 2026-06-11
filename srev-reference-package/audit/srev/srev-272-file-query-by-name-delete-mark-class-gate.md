# SREV-272: File Query-By-Name Delete-Mark Class Gate

## Stage Gate

| Field | Value |
|---|---|
| Stage | schema -> topology -> logic -> action -> verify |
| Input artifact | `Sandboxie/core/dll/file.c`, Microsoft `NtQueryInformationByName` and `FILE_BASIC_INFORMATION` documentation |
| Output artifact | `docs/plan/srev-272-file-query-by-name-delete-mark-class-gate.schema.json`, `docs/plan/check-srev-272.py`, `docs/plan/check-srev-272.sh`, ledger fragment, comment-only source clarification |
| Owner | `File_NtQueryInformationByName` copy-path query and future delete-mark filtering |
| Acceptance gate | targeted source checker, core coverage, and diff checkpoint |

## Evidence

`File_NtQueryInformationByName` first queries the sandbox copy path. If that
copy-path query succeeds or returns a status other than name/path-not-found, it
leaves before trying the true path.

The source had a bare `// todo` above a commented-out legacy delete-mark check:

```text
if (!File_Delete_v2) {
    if (NT_SUCCESS(status) && IS_DELETE_MARK(&FileInformation->CreationTime))
        status = STATUS_OBJECT_NAME_NOT_FOUND;
}
```

That code cannot be restored as-is. `FileInformation` is a `PVOID`, and its
layout is determined by `FileInformationClass`. Treating it as a structure with
`CreationTime` is legal only after the class and `Length` prove that layout.

## Official Shape

Microsoft documents `NtQueryInformationByName` as returning information about a
file specified by name without opening the file. Its `FileInformation` parameter
is a caller-supplied buffer, and the structure of that buffer is determined by
`FileInformationClass`.

Microsoft documents the supported `NtQueryInformationByName` classes as
including `FileStatInformation`, `FileStatLxInformation`,
`FileCaseSensitiveInformation`, and `FileStatBasicInformation`; it does not
document a universal `CreationTime` member for all classes.

Microsoft documents `FILE_BASIC_INFORMATION` as a distinct structure whose
`CreationTime`, access/write/change times, and attributes exist only when the
caller requested a class with that layout.

```text
https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/nf-ntifs-ntqueryinformationbyname
https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/ns-wdm-_file_basic_information
```

## Data

`File_NtQueryInformationByName`, `FileInformationClass`, `FileInformation`,
`Length`, `CopyPath`, `__sys_NtQueryInformationByName`, `File_Delete_v2`,
`IS_DELETE_MARK`, `FILE_BASIC_INFORMATION.CreationTime`, and the copy-path
leave-before-true-path decision.

## Schema

`FILE_QUERY_BY_NAME_DELETE_MARK_CLASS_GATE` says:

- `NtQueryInformationByName` output layout is owned by `FileInformationClass`;
- delete-mark filtering may inspect `CreationTime` only for classes whose output
  schema has a compatible `CreationTime` member and when `Length` covers that
  field;
- `FileInformation` must not be treated as `FILE_BASIC_INFORMATION` for all
  query-by-name classes;
- the current commented legacy check remains disabled until a class-specific
  parser is added;
- this SREV changes comments and proof only; copy-path/true-path routing and
  delete-v2 policy are unchanged.

## Topology

```text
caller NtQueryInformationByName
  -> ObjectAttributes / FileInformationClass / output buffer
  -> Sandboxie copy-path query
  -> class-specific output layout
  -> future delete-mark parser only after class + Length proof
  -> leave on copy-path result or continue to true-path fallback
```

## Logic Risk

Re-enabling the old check blindly would couple the delete-marker policy to the
wrong schema. Some query-by-name classes do not expose `CreationTime` in the
same position, and a short `Length` can make even a compatible class unsafe to
inspect. Leaving the bare `todo` also hides the reason the code is disabled and
invites a future accidental `PVOID` reinterpretation.

## Fix

Comment-only source clarification. The bare `// todo` now names SREV-272 and
states that delete-mark filtering for `NtQueryInformationByName` requires a
class-specific output parser and a length gate before treating
`FileInformation` as a structure with `CreationTime`. No behavior changed.

## Acceptance Gate

`docs/plan/check-srev-272.py` validates the draft-07 schema, official references,
source comment owner, disabled legacy check, copy-path query topology,
absence of the bare `// todo`, and the ledger fragment.

Runtime gate: Windows `NtQueryInformationByName` matrix for supported
`FileInformationClass` values, including copy-path delete-marker cases, proving
any future class-specific parser hides deleted copy-path entries without reading
outside the returned buffer or misclassifying unsupported classes.
