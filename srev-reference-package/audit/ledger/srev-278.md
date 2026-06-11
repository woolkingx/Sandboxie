---
kind: srev-ledger-entry
id: SREV-278
title: Directory Enumeration Progress Gate
status: patched-comment-topology-after-official-directory-enumeration-progress-review-no-behavior-change
owner: Sandboxie/core/dll/file_dir.c
spec: docs/plan/srev-278-directory-enumeration-progress-gate.md
schema: docs/plan/srev-278-directory-enumeration-progress-gate.schema.json
checker: docs/plan/check-srev-278.py
runtime_gate: Windows directory enumeration provider progress matrix
---

### SREV-278: Directory Enumeration Progress Gate

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | patched comment/topology after official directory-enumeration progress review; no behavior change |
| Evidence | `File_MergeCache` repeatedly calls `__sys_NtQueryDirectoryFile(... FileIdBothDirectoryInformation ...)`, copies each returned `FILE_ID_BOTH_DIR_INFORMATION` into a merge-cache entry, and inserts entries into a sorted list. The source had vendor-specific comments saying an Isilon provider repeats the same name while returning success. The actual local invariant is that enumeration must make progress before publishing another cache entry. |
| Data | `File_MergeCache`, `qfile->RestartScan`, `FileMask`, `__sys_NtQueryDirectoryFile`, `IoStatusBlock`, `FILE_ID_BOTH_DIR_INFORMATION`, `NextEntryOffset`, `FileNameLength`, `FILE_MERGE_CACHE_FILE`, `name_uni`, `RtlCompareUnicodeString`, `cmp == 0`, `STATUS_NO_MORE_FILES`, `List_Insert_Before`, and `List_Insert_After`. |
| Schema | `DIRECTORY_ENUMERATION_PROGRESS_GATE` says `File_MergeCache` owns progress safety while building the sorted directory merge cache; `NtQueryDirectoryFile` returns one or more `FILE_XXX_INFORMATION` records and ends with an empty buffer plus a status such as `STATUS_NO_MORE_FILES`; `RestartScan` starts enumeration at the first entry and subsequent calls continue the scan; `FILE_ID_BOTH_DIR_INFORMATION` is a variable-size record whose next entry is located by `NextEntryOffset`; `FileNameLength` is a byte count used to create the cache entry name view; a provider result that repeats a name already present in the merge cache is non-progress at this owner boundary; the duplicate-name progress guard synthesizes `STATUS_NO_MORE_FILES` before publication of the duplicate entry; SREV-001 owns variable-size record capacity and `NextEntryOffset` buffer-shape proof; this SREV changes comments and proof only. |
| Topology | `NtQueryDirectoryFile -> info_area records -> FILE_ID_BOTH_DIR_INFORMATION.FileNameLength -> cache_file->name_uni -> ordered cache_list comparison -> cmp < 0 / > 0 insert before/after -> cmp == 0 synthesize STATUS_NO_MORE_FILES and stop`. |
| Logic Risk | Treating the branch as a vendor-only workaround hides the general merge-cache invariant. If a provider repeats a name, inserting it would duplicate a published entry and continuing the loop would wait for an end status that may not arrive. The correct local response is to stop at the progress boundary while preserving all unique entries already cached. |
| Official Shape | Microsoft documents `NtQueryDirectoryFile` as returning directory entries in `FILE_XXX_INFORMATION` records and ending with an empty output buffer plus a status such as `STATUS_NO_MORE_FILES`. Microsoft documents `FILE_ID_BOTH_DIR_INFORMATION.NextEntryOffset` as the next-entry byte offset and `FileNameLength` as the file-name byte length. MS-FSCC documents that `NextEntryOffset` must locate the next entry and `FileNameLength` must be used rather than assuming a trailing NUL. |
| Fix | Comment-only source clarification. The vendor-specific symptom comment now names SREV-278 and states the progress invariant: repeated names already present in the merge cache are treated as end-of-enumeration by synthesizing `STATUS_NO_MORE_FILES`. No behavior changed. |
| Acceptance Gate | `docs/plan/check-srev-278.py` validates the draft-07 schema, official references, SREV-001 adjacency, `NtQueryDirectoryFile` call shape, `FILE_ID_BOTH_DIR_INFORMATION` copy and name view, ordered cache insertion, `cmp == 0` progress guard, stale vendor-symptom wording removal, and ledger fragment; `docs/plan/check-srev-278.sh` is the targeted wrapper. Runtime gate: Windows directory enumeration matrix covering NTFS, FAT/exFAT or secondary cache path, an SMB/NAS provider with repeated-name behavior, wildcard `FileMask`, restart-scan behavior, and duplicate-name progress termination without losing unique entries. |
