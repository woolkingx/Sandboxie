# SREV-286: Snapshot Path Builder TLS Gate

## Stage Gate

| Field | Value |
|---|---|
| Stage | schema -> boundary -> topology -> logic -> action -> verify |
| Input artifact | `Sandboxie/core/dll/file_snapshots.c`, SREV-060, SREV-196, Microsoft CRT wide-string copy references |
| Output artifact | Source-level TLS buffer gate, draft-07 schema, targeted checker, ledger fragment |
| Owner | `File_MakeSnapshotPath` snapshot path builder |
| Acceptance gate | `docs/plan/check-srev-286.py`, `docs/plan/check-srev-286.sh`, core coverage, and diff checkpoint |

## Data

`File_MakeSnapshotPath` builds a snapshot copy path from:

```text
Cur_Snapshot
CopyPath
File_FindBoxPrefix(CopyPath)
Dll_GetTlsNameBuffer(... TMPL_NAME_BUFFER ...)
File_Snapshot_Prefix
Cur_Snapshot->ID
CopyPath + prefixLen
```

`File_GetPathFlagsEx` and `File_FindSnapshotPath` call the builder and already
treat a null builder result as a stop condition. Before this SREV, the builder
could still pass a failed TLS name-buffer allocation into `wcsncpy` and `wcscpy`
before returning null.

## Official Shape

Microsoft documents `wcscpy` as copying the source string, including the
terminating null character, into the destination and returning the destination.
No return value is reserved for an error, and the function does not check for
sufficient destination space before copying.

Microsoft documents `wcsncpy` as copying a caller-provided character count from
source to destination.

Official references:

- `https://learn.microsoft.com/en-us/cpp/c-runtime-library/reference/strcpy-wcscpy-mbscpy?view=msvc-170`
- `https://learn.microsoft.com/en-us/cpp/c-runtime-library/reference/strncpy-strncpy-l-wcsncpy-wcsncpy-l-mbsncpy-mbsncpy-l?view=msvc-170`

## Local Shape

SREV-196 proves `Dll_GetTlsNameBuffer` may return null on allocation failure and
that failed name-buffer allocations must not be published as valid TLS buffers.
SREV-265 records one caller-side consequence: callers must check the returned
TLS name buffer before copying into it.

SREV-060 owns the adjacent snapshot relocation copy-path conversion gate. This
SREV does not change relocation semantics, prefix selection, snapshot traversal,
or `File_Delete_v2` behavior.

## Schema

Local schema:

```text
docs/plan/srev-286-snapshot-path-builder-tls-gate.schema.json
```

Contract id:

```text
SNAPSHOT_PATH_BUILDER_TLS_GATE
```

The builder contract is:

```text
Cur_Snapshot != NULL
CopyPath has boxed prefix
TMPL_NAME_BUFFER allocation succeeds
-> wcsncpy/wcscpy may write snapshot path
```

## Boundary

```text
CopyPath + snapshot metadata
  -> File_MakeSnapshotPath owner
  -> TMPL_NAME_BUFFER allocation gate
  -> snapshot path string publication
  -> caller RtlInitUnicodeString/File_GetFileType
```

The builder owns proving the temporary destination buffer before any string copy
writes into it. Callers own deciding whether a missing builder result stops
snapshot traversal.

## Topology

```text
File_GetPathFlagsEx / File_FindSnapshotPath
  -> File_MakeSnapshotPath
    -> File_FindBoxPrefix
    -> Dll_GetTlsNameBuffer(TMPL_NAME_BUFFER)
    -> non-null gate
    -> wcsncpy/wcscpy path assembly
  -> RtlInitUnicodeString + File_GetFileType
```

## Logic Risk

The caller-side null check made it look as if path-building failure was already
handled. The missing owner-local gate was inside the builder, where the first
write to `TmplName` happened immediately after the fallible TLS allocation.
Under allocation pressure, the builder could turn a recoverable missing path
publication into a null destination write before callers had a chance to stop.

## Fix

`File_MakeSnapshotPath` now returns null immediately if
`Dll_GetTlsNameBuffer(... TMPL_NAME_BUFFER ...)` fails. `File_GetPathFlagsEx`
keeps the same stop behavior but replaces the stale comment with an owner-tagged
SREV-286 note. No snapshot traversal or relocation policy changed.

## Acceptance Gate

`docs/plan/check-srev-286.py` validates the draft-07 schema, official
references, SREV-196/SREV-060 adjacency, the builder null gate before the first
`wcsncpy` write, both caller stop gates, stale source comment removal, combined
ledger entry, and split ledger fragment.

Runtime gate: Windows snapshot matrix with active snapshot chain, boxed copy
path, parent-snapshot hit, prefix miss, TLS allocation failure injection for
`TMPL_NAME_BUFFER`, relocation refresh, and `File_Delete_v2` true/false.
