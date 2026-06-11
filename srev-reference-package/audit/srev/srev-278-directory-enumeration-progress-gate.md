# SREV-278: Directory Enumeration Progress Gate

| Field | Content |
|---|---|
| Stage | schema -> topology -> verify |
| Input artifact | `Sandboxie/core/dll/file_dir.c`, SREV-001, Microsoft `NtQueryDirectoryFile`, `FILE_ID_BOTH_DIR_INFORMATION`, and MS-FSCC FileIdBothDirectoryInformation documentation |
| Output artifact | Source comment owner, draft-07 schema, checker, and ledger fragment |
| Owner | `File_MergeCache` directory merge-cache enumeration |
| Acceptance gate | Targeted checker validates official references, repeated-name progress guard, cache insertion topology, stale vendor-symptom wording removal, and ledger fragment |

## Data

`File_MergeCache` builds a sorted cache of directory entries by repeatedly
calling `__sys_NtQueryDirectoryFile` with
`FileIdBothDirectoryInformation`. It copies each returned
`FILE_ID_BOTH_DIR_INFORMATION` entry into a `FILE_MERGE_CACHE_FILE`, gives the
entry a `UNICODE_STRING` view over the copied `FileName`, and inserts the node
into `qfile->cache_list` in case-insensitive order.

Before inserting a new node, the function compares the returned name against the
current sorted list. If the provider returns a name already present in the merge
cache, `cmp == 0`; the code sets `status = STATUS_NO_MORE_FILES` and exits the
enumeration loop.

## Official Shape

Microsoft documents `NtQueryDirectoryFile` as returning one or more
`FILE_XXX_INFORMATION` directory entries per call. `RestartScan` starts at the
first entry; subsequent calls continue the enumeration. The final call returns
an empty output buffer with a status such as `STATUS_NO_MORE_FILES`.

Microsoft documents `FILE_ID_BOTH_DIR_INFORMATION` as a variable-size directory
entry structure. `NextEntryOffset` points to the next entry in the returned
buffer, and `FileNameLength` is the byte length of the file name. MS-FSCC
documents the same shape and says `NextEntryOffset` must be used to locate the
next entry and `FileNameLength` must be used instead of assuming a trailing
NUL.

Official references:

- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/nf-ntifs-ntquerydirectoryfile`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/ns-ntifs-_file_id_both_dir_information`
- `https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-fscc/1e144bff-c056-45aa-bd29-c13d214ee2ba`

## Boundary

```text
directory provider enumeration
  -> NtQueryDirectoryFile output buffer
  -> FILE_ID_BOTH_DIR_INFORMATION records
  -> Sandboxie sorted merge cache
  -> progress guard before list publication
```

The provider owns enumeration status and returned records. `File_MergeCache`
owns progress safety while building Sandboxie's sorted cache. If the provider
continues returning a name that is already in the cache, the local merge owner
must stop the loop rather than inserting a duplicate or waiting for an end status
that never arrives.

## Topology

```text
NtQueryDirectoryFile
  -> info_area records
  -> FILE_ID_BOTH_DIR_INFORMATION.FileNameLength
  -> cache_file->name_uni
  -> ordered cache_list comparison
  -> cmp < 0 / > 0: insert before/after
  -> cmp == 0: synthesize STATUS_NO_MORE_FILES and stop
```

SREV-001 owns variable-size record capacity and `NextEntryOffset` buffer-shape
proof. SREV-278 owns enumeration progress at the merge-cache publication edge.

## Logic Risk

The old comment named a vendor symptom and an infinite-loop outcome, but it did
not identify the general invariant: a directory scan that repeats a previously
published name has stopped making progress. Treating this as a vendor-only hack
could invite removal or narrowing even though the progress guard is the local
merge-cache safety boundary.

## Fix

Comment-only source clarification. The vendor-specific symptom comment now
names SREV-278 and states the progress invariant: repeated names already present
in the merge cache are treated as end-of-enumeration by synthesizing
`STATUS_NO_MORE_FILES`. No behavior changed.

## Acceptance Gate

`docs/plan/check-srev-278.py` validates the draft-07 schema, official
references, SREV-001 adjacency, `NtQueryDirectoryFile` call shape,
`FILE_ID_BOTH_DIR_INFORMATION` copy and name view, ordered cache insertion,
`cmp == 0` progress guard, stale vendor-symptom wording removal, and ledger
fragment.

Runtime gate: Windows directory enumeration matrix covering NTFS, FAT/exFAT or
secondary cache path, an SMB/NAS provider with repeated-name behavior, wildcard
`FileMask`, restart-scan behavior, and duplicate-name progress termination
without losing unique entries.
