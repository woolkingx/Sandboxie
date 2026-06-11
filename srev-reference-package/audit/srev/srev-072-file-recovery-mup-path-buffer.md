# SREV-072: File Recovery MUP Path Buffer

## Data

`Sandboxie/core/dll/file_recovery.c` normalizes network redirector paths before
checking whether a file is recoverable. Paths such as LanmanRedirector, DFS,
HGFS, or MUP redirector forms can be translated into the `\Device\Mup\...`
shape used by the driver-side recovery folder records.

The relevant data nodes are:

```text
incoming TruePath
redirector prefix
post-prefix share path
allocated MUP translation buffer
File_RecoverFolders comparison path
```

## Official Shape

Microsoft documents `wmemcpy` as copying wide characters from source to
destination buffers:

```text
https://learn.microsoft.com/en-us/cpp/c-runtime-library/reference/memcpy-wmemcpy?view=msvc-170
```

That local copy is legal only when the destination buffer allocation succeeded.

## Schema

Local schema:

```text
docs/plan/srev-072-file-recovery-mup-path-buffer.schema.json
```

The redirector-to-MUP translation contract is:

```text
path2 != NULL before writing File_Mup into it
path2 != NULL before appending the share suffix
TruePath changes to path2 only after the translated buffer is fully initialized
allocation failure keeps the original TruePath and skips only local normalization
```

## Topology

```text
TruePath -> optional redirector normalization buffer -> recover-folder comparison
```

`File_IsRecoverable` owns only the temporary normalized path buffer. The recovery
folder list comparison may use either the original path or the proven translated
path, but it must not read or write a null translation buffer.

## Logic Risk

Before this patch, `File_IsRecoverable` allocated `path2` and immediately copied
into it with `wmemcpy`. A low-memory failure could crash the recovery check while
processing a network redirector path. The normalization is a compatibility
projection, so allocation failure should skip the projection rather than
dereference a null destination.

## Fix

The redirector-to-MUP branch now checks `path2` before both `wmemcpy` calls and
before assigning it to `TruePath`. If allocation fails, the function continues
with the original path.

## Acceptance Gate

`docs/plan/check-srev-072.py` validates the draft-07 schema, official `wmemcpy`
reference, allocation gate before MUP-prefix copy, suffix copy inside the same
gate, `TruePath` reassignment only after initialization, and ledger entry.

Windows gate: recoverable network redirector paths still normalize to
`\Device\Mup\...` when allocation succeeds; low-memory allocation failure does
not crash and falls back to comparing the original path.
