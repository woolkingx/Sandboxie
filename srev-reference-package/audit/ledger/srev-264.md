---
kind: srev-ledger-entry
id: SREV-264
title: File AltBoxPath Legacy Prefix Owner
status: patched-comment-topology-after-srev-057-raw-root-mount-point-review-no-behavior-change
owner: Sandboxie/core/dll/file.c
spec: docs/plan/srev-264-file-altboxpath-legacy-prefix-owner.md
schema: docs/plan/srev-264-file-altboxpath-legacy-prefix-owner.schema.json
checker: docs/plan/check-srev-264.py
runtime_gate: Windows box-root/mount-point matrix inherited from SREV-057
---

### SREV-264: File AltBoxPath Legacy Prefix Owner

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | patched comment/topology after SREV-057 raw-root mount-point review; no behavior change |
| Evidence | `File_FindBoxPrefix` checks three box-root prefixes: `Dll_BoxFilePath`, `Dll_BoxFileRawPath`, and `File_AltBoxPath`. The old inline comment on `File_AltBoxPath` said it was deprecated and should be removed because raw path was more reliable. That wording hid an owner boundary: `File_AltBoxPath` is published by the mount-point path conversion block in `file_init.c`, while SREV-057 owns the raw-root and DOS-path publication matrix. |
| Data | `File_FindBoxPrefix`, `Dll_BoxFilePath`, `Dll_BoxFileRawPath`, `File_AltBoxPath`, `File_AltBoxPathLen`, `File_GetName_ConvertLinks`, mount-point converted true path, and SREV-057. |
| Schema | `FILE_ALTBOXPATH_LEGACY_PREFIX_OWNER` says `File_FindBoxPrefix` owns the ordered box-root prefix set used by later path gates; `File_AltBoxPath` is a legacy mount-point prefix fallback, not an immediately removable dead field; removal requires Windows proof that SREV-057 raw-root / mount-point fallback paths still cover every prefix-matching consumer; this SREV does not change prefix order, matching semantics, raw-root publication, DOS translation, mount-point conversion, or file policy. |
| Topology | `file_init mount-point conversion -> File_AltBoxPath + File_AltBoxPathLen -> File_FindBoxPrefix ordered prefix list -> downstream boxed-path prefix gate`. |
| Logic Risk | A `deprecated, remove` comment can drive the wrong action: deleting a legacy prefix before proving the raw-root route covers directory mount-point behavior. That would turn a comment-cleanup task into a path-escape or false-negative boxed-prefix regression. |
| Official Shape | Microsoft documents reparse points as file-system objects whose filter-owned data can cause file opens to be processed differently, and documents that reparse points are used to implement mounted folders. |
| Fix | Comment-only source clarification. The source now says `File_AltBoxPath` is a legacy mount-point prefix fallback and that removal must first reprove the SREV-057 raw-root/mount-point matrix. SREV-265 later added the allocation/publication gate for this fallback. |
| Acceptance Gate | `docs/plan/check-srev-264.py` validates the draft-07 schema, official references, source comment, unchanged three-prefix order, `file_init.c` mount-point publication evidence, SREV-057 adjacency, and the ledger fragment; `docs/plan/check-srev-264.sh` is the targeted wrapper. Runtime gate is inherited from SREV-057. |
