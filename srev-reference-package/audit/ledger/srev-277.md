---
kind: srev-ledger-entry
id: SREV-277
title: FilePaths Unknown-Drive Sentinel
status: patched-comment-topology-after-filepaths-unknown-drive-sentinel-review-no-behavior-change
owner: Sandboxie/core/dll/file_del.c
spec: docs/plan/srev-277-filepaths-unknown-drive-sentinel.md
schema: docs/plan/srev-277-filepaths-unknown-drive-sentinel.schema.json
checker: docs/plan/check-srev-277.py
runtime_gate: Windows FilePaths.dat unknown-drive round-trip matrix
---

### SREV-277: FilePaths Unknown-Drive Sentinel

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | patched comment/topology after FilePaths.dat unknown-drive sentinel review; no behavior change |
| Evidence | `File_TranslateNtToDosPathForDatFile` had a `Hack Hack` comment over a branch that strips a leading backslash from paths shaped like `L"\\C:\\path"`. The adjacent load/save topology shows this is a persistence sentinel for a drive-letter path whose current NT mapping is unavailable, not an arbitrary hack. |
| Data | `FilePaths.dat`, `File_LoadPathTree_internal`, `File_SavePathTree_internal`, `File_TranslateDosToNtPathForDatFile`, `File_TranslateNtToDosPathForDatFile`, `File_GetDriveForLetter`, `File_GetDriveForPath`, `File_GetDriveForUncPath`, `PATH_NODE`, `Dll_BoxFilePath`, `File_Mup`, and the leading-backslash drive-letter sentinel. |
| Schema | `FILEPATHS_UNKNOWN_DRIVE_SENTINEL` says load-time projection maps drive-letter paths through MS-DOS device namespace links; unavailable drive-letter paths must be preserved rather than silently dropped; the leading-backslash sentinel represents a preserved DOS drive-letter path with unknown NT target; save-time stripping is legal only when the colon immediately precedes the first path separator or terminator after the leading backslash; known NT paths still use MUP, drive, or UNC mapping; this SREV changes comments and proof only. |
| Topology | `FilePaths.dat -> File_LoadPathTree_internal -> File_TranslateDosToNtPathForDatFile -> PATH_NODE tree -> File_SavePathTree_internal -> File_TranslateNtToDosPathForDatFile -> FilePaths.dat`. Available drives become true NT paths. Unavailable drives stay as a reversible sentinel and are written back as the original DOS drive-letter path. |
| Logic Risk | Removing the branch would lose delete/relocation entries for currently unavailable drives. Broadening it would corrupt real NT paths that happen to contain a colon later in the path. The sentinel strip is legal only for a preserved drive-letter sentinel at the first path component. |
| Official Shape | Microsoft documents drive letters and MS-DOS device names as object-namespace junctions. `QueryDosDevice` can query those junctions and says MS-DOS path conversion uses them to map drive letters and DOS devices. Microsoft also documents local and global MS-DOS device namespaces, making unavailable drive mappings a real context-dependent state. |
| Fix | Comment-only source clarification. The branch now names SREV-277 and describes the leading-backslash unknown-drive sentinel used to preserve `FilePaths.dat` entries across missing drive mappings. No behavior changed. |
| Acceptance Gate | `docs/plan/check-srev-277.py` validates the draft-07 schema, official references, `File_TranslateDosToNtPathForDatFile` load-time drive mapping, `File_TranslateNtToDosPathForDatFile` save-time sentinel strip, stale hack wording removal, and ledger fragment; `docs/plan/check-srev-277.sh` is the targeted wrapper. Runtime gate: Windows FilePaths.dat round trip with an available drive letter, an unavailable/removable drive-letter path, UNC/MUP path, volume serial suffix mode, and reappearance of the drive mapping after reload. |
