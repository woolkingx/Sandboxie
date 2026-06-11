# SREV-264: File AltBoxPath Legacy Prefix Owner

## Stage Gate

| Field | Value |
|---|---|
| Stage | schema -> topology -> logic -> action -> verify |
| Input artifact | `Sandboxie/core/dll/file.c`, `Sandboxie/core/dll/file_init.c`, SREV-057, Microsoft reparse-point documentation |
| Output artifact | `docs/plan/srev-264-file-altboxpath-legacy-prefix-owner.schema.json`, `docs/plan/check-srev-264.py`, `docs/plan/check-srev-264.sh`, ledger fragment, comment-only source clarification |
| Owner | `File_FindBoxPrefix` box-root prefix list |
| Acceptance gate | targeted source checker plus SREV-057 adjacency checker, core coverage, and diff checkpoint |

## Evidence

`File_FindBoxPrefix` checks three box-root prefixes: `Dll_BoxFilePath`,
`Dll_BoxFileRawPath`, and `File_AltBoxPath`. The old inline comment on
`File_AltBoxPath` said it was deprecated and should be removed because raw path
was more reliable. That wording hid an owner boundary: `File_AltBoxPath` is
published by the mount-point path conversion block in `file_init.c`, while
SREV-057 owns the raw-root and DOS-path publication matrix.

## Official Shape

Microsoft documents reparse points as file-system objects whose filter-owned
data can cause file opens to be processed differently. Microsoft also documents
that reparse points are used to implement mounted folders. This means mounted
folder and reparse-target path behavior cannot be reduced to a single raw-root
string without Windows runtime proof.

```text
https://learn.microsoft.com/en-us/windows/win32/fileio/reparse-points
https://learn.microsoft.com/en-us/windows/win32/fileio/reparse-points-and-file-operations
```

## Data

`File_FindBoxPrefix`, `Dll_BoxFilePath`, `Dll_BoxFileRawPath`,
`File_AltBoxPath`, `File_AltBoxPathLen`, `File_GetName_ConvertLinks`,
mount-point converted true path, and SREV-057.

## Schema

`FILE_ALTBOXPATH_LEGACY_PREFIX_OWNER` says:

- `File_FindBoxPrefix` owns the ordered box-root prefix set used by later path
  gates;
- `File_AltBoxPath` is a legacy mount-point prefix fallback, not an immediately
  removable dead field;
- removal requires Windows proof that SREV-057 raw-root / mount-point fallback
  paths still cover every prefix-matching consumer;
- this SREV does not change prefix order, matching semantics, raw-root
  publication, DOS translation, mount-point conversion, or file policy.

## Topology

```text
file_init mount-point conversion
  -> File_AltBoxPath + File_AltBoxPathLen
  -> File_FindBoxPrefix ordered prefix list
  -> downstream boxed-path prefix gate
```

## Logic Risk

A `deprecated, remove` comment can drive the wrong action: deleting a legacy
prefix before proving the raw-root route covers directory mount-point behavior.
That would turn a comment-cleanup task into a path-escape or false-negative
boxed-prefix regression.

## Fix

Comment-only source clarification. The source now says `File_AltBoxPath` is a
legacy mount-point prefix fallback and that removal must first reprove the
SREV-057 raw-root/mount-point matrix. No behavior changed.

SREV-265 later added the allocation/publication gate for this fallback: the
temporary TLS path buffer is checked before copy, and `File_AltBoxPath` is
published only after the dedicated allocation succeeds and is initialized.

## Acceptance Gate

`docs/plan/check-srev-264.py` validates the draft-07 schema, official
references, source comment, unchanged three-prefix order, `file_init.c`
mount-point publication evidence, SREV-057 adjacency, and the ledger fragment.

Runtime gate: Windows box-root/mount-point matrix inherited from SREV-057.
