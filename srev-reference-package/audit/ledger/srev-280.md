---
kind: srev-ledger-entry
id: SREV-280
title: Box Root Raw Path Fallback Owner
status: patched-comment-topology-after-official-namespace-raw-root-fallback-review-no-behavior-change
owner: Sandboxie/core/dll/file_init.c
spec: docs/plan/srev-280-box-root-raw-path-fallback-owner.md
schema: docs/plan/srev-280-box-root-raw-path-fallback-owner.schema.json
checker: docs/plan/check-srev-280.py
runtime_gate: Windows box-root raw-path fallback matrix
---

### SREV-280: Box Root Raw Path Fallback Owner

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | patched comment/topology after official namespace raw-root fallback review; no behavior change |
| Evidence | `File_Init` first tries to publish `Dll_BoxFileDosPath` by translating `Dll_BoxFilePath`. If that translation misses, it queries the driver-published raw root through `SbieApi_QueryProcessInfoStr(0, 'root', ...)`, stages the result locally, publishes `Dll_BoxFileRawPath`, and runs the same translator before publishing `Dll_BoxFileDosPathLen`. The old comment called this a workaround and pointed only at the translator, hiding the initialization owner boundary. |
| Data | `Dll_BoxFilePath`, `Dll_BoxFileDosPath`, `Dll_BoxFileDosPathLen`, `SbieDll_TranslateNtToDosPath`, `SbieApi_QueryProcessInfoStr(0, 'root', ...)`, `BoxFileRawPathLen`, `BoxFileRawPath`, `Dll_BoxFileRawPath`, `Dll_BoxFileRawPathLen`, SREV-057, and SREV-276. |
| Schema | `BOX_ROOT_RAW_PATH_FALLBACK_OWNER` says `File_Init` owns box-root raw-path fallback publication; Windows path strings are namespace-specific presentations; MS-DOS device names are object-namespace junctions; `QueryDosDevice` exposes MS-DOS device namespace mappings; local and global DosDevices contexts can expose different DOS presentations; raw-root fallback may query the driver-published box root only after normal DOS projection misses; raw-root fallback must reuse `SbieDll_TranslateNtToDosPath` rather than inventing a generic device rewrite; SREV-057 owns raw-root byte-capacity and global-publication gates; SREV-276 owns the NT-to-DOS namespace translator; this SREV changes comments and proof only. |
| Topology | `Dll_BoxFilePath -> Dll_BoxFileDosPath allocation -> SbieDll_TranslateNtToDosPath`. On translation miss: `SbieApi_QueryProcessInfoStr root byte-capacity query -> bounded local raw-root buffer -> second query + non-empty proof -> publish Dll_BoxFileRawPath + Dll_BoxFileRawPathLen -> Dll_BoxFileDosPath allocation -> SbieDll_TranslateNtToDosPath -> Dll_BoxFileDosPathLen publication`. |
| Logic Risk | The old comment could drive future edits toward broad namespace rewriting in `SbieDll_TranslateNtToDosPath` even though the safer owner is the bounded driver-published raw-root fallback in `File_Init`. That would blur initialization publication with generic NT-device to Win32-device conversion. |
| Official Shape | Microsoft documents NT, Win32 file, and Win32 device namespaces as distinct path presentations. Microsoft documents MS-DOS device names as object-namespace junctions and documents `QueryDosDevice` as the API for reading those mappings. Microsoft also documents local and global DosDevices contexts, so caller-visible DOS presentation is context-sensitive. |
| Fix | Comment-only source clarification. The source now names SREV-280 and states that if the normal box root lacks a caller-visible DOS presentation, `File_Init` queries the driver-published raw root and runs the same namespace translator before publishing lengths. No behavior changed. |
| Acceptance Gate | `docs/plan/check-srev-280.py` validates the draft-07 schema, official references, `file_init.c` direct and raw-root fallback shape, raw-root query and publication gates inherited from SREV-057, namespace translator adjacency from SREV-276, stale source wording removal, and ledger fragment; `docs/plan/check-srev-280.sh` is the targeted wrapper. Runtime gate: Windows box-root matrix covering ordinary drive-letter roots, reparse or mount-point roots whose target device lacks a caller-visible DOS presentation, local/global DosDevices visibility, raw-query failure, empty raw-root response, and fallback allocation failure. |
