# SREV-060: File Snapshot Relocation Copy Path Gate

## Data

Snapshot lookup and merge paths translate a relocated true path back into a copy
path before checking parent snapshots.

Affected owners:

```text
Sandboxie/core/dll/file_snapshots.c
Sandboxie/core/dll/file_dir.c
```

The relevant data nodes are:

```text
TmplRelocation / Relocation
File_GetName NTSTATUS
TruePath2
CopyPath2
current CopyPath
parent snapshot lookup or merge state
```

## Official Shape

Microsoft documents `wcslen` as accepting a null-terminated wide string:

```text
https://learn.microsoft.com/en-us/cpp/c-runtime-library/reference/strlen-wcslen-mbslen-mbslen-l-mbstrlen-mbstrlen-l?view=msvc-170
```

Microsoft documents the wide-string copy family as requiring a non-null source
and a destination large enough for the source plus terminator:

```text
https://learn.microsoft.com/en-us/cpp/c-runtime-library/reference/strcpy-s-wcscpy-s-mbscpy-s?view=msvc-170
```

Microsoft documents `NT_SUCCESS` as the system-supplied success predicate for
`NTSTATUS` values:

```text
https://learn.microsoft.com/en-gb/windows-hardware/drivers/kernel/using-ntstatus-values
```

## Local Shape

`File_GetName` initializes `*OutTruePath` and `*OutCopyPath` to `NULL` before it
does any conversion work. A caller may use `CopyPath2` as a null-terminated
source string only after `NT_SUCCESS(status)` and non-null output proof.

## Schema

Local schema:

```text
docs/plan/srev-060-file-snapshot-relocation-copy-path.schema.json
```

Relocation-to-copy-path conversion has this contract:

```text
relocation true path -> File_GetName -> NT_SUCCESS + CopyPath2 != NULL -> wcslen/wcscpy
```

Failure must not feed `CopyPath2` into string functions and must not continue
parent snapshot lookup with a stale previous `CopyPath`.

## Topology

```text
current snapshot relocation -> File_GetName owner -> copy-path buffer -> parent snapshot lookup
```

`File_GetName` owns the legal conversion from true path to copy path. Snapshot
lookup owns the decision to continue only when that conversion succeeded.

## Logic Risk

Before this patch, both snapshot paths called `File_GetName` and ignored the
returned `NTSTATUS`. Because `File_GetName` starts by setting output pointers to
`NULL`, a conversion failure could send `CopyPath2 == NULL` into `wcslen` and
`wcscpy`. Worse, if a relocation could not be converted, continuing with the
older `CopyPath` would query or merge the wrong snapshot path.

## Fix

`File_GetPathFlagsEx` now initializes `TruePath2`/`CopyPath2`, checks
`NT_SUCCESS(status) && CopyPath2`, and disables the copy-path branch when the
relocated path cannot be converted.

The directory merge path now initializes `TruePath2`/`CopyPath2`, checks
`NT_SUCCESS(status) && CopyPath2`, and stops parent snapshot traversal when the
relocation cannot produce a legal copy path.

## Acceptance Gate

`docs/plan/check-srev-060.py` validates the draft-07 schema, official reference
links, local `File_GetName` null-output shape, both caller gates, stale-copy-path
prevention, and ledger entry.

Windows gate: snapshot lookup and directory merge with a valid relocation should
preserve behavior; malformed/unmappable relocation should avoid null dereference
and avoid parent snapshot lookup with the previous copy path.
