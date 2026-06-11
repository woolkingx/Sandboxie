---
kind: srev-ledger-entry
id: SREV-276
title: NT-To-DOS Namespace Boundary
status: patched-comment-topology-after-official-nt-dos-namespace-review-no-behavior-change
owner: Sandboxie/core/dll/file.c
spec: docs/plan/srev-276-nt-to-dos-namespace-boundary.md
schema: docs/plan/srev-276-nt-to-dos-namespace-boundary.schema.json
checker: docs/plan/check-srev-276.py
runtime_gate: Windows NT/DOS namespace path-presentation matrix
---

### SREV-276: NT-To-DOS Namespace Boundary

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | patched comment/topology after official NT/DOS namespace review; no behavior change |
| Evidence | `SbieDll_TranslateNtToDosPath` mutates a path buffer into a caller-visible DOS/Win32 presentation when a known mapping exists. It had one comment calling the hidden Sandboxie box-root mapping a workaround and another disabled `\Device\` to `\\.\` fallback comment with `fix me` / Chrome crash-handler hang wording. |
| Data | `SbieDll_TranslateNtToDosPath`, `\??\` prefix stripping, `File_Mup`, `Dll_BoxFilePath`, `Dll_BoxFileDosPath`, `File_GetDriveForPath`, `File_GetDriveForUncPath`, `File_DrivesAndLinks_CritSec`, disabled `\Device\` fallback, and final `FALSE` return for unmapped paths. |
| Schema | `NT_TO_DOS_NAMESPACE_BOUNDARY` says `SbieDll_TranslateNtToDosPath` owns caller-visible path presentation for known NT-to-DOS mappings; MS-DOS device names are object-namespace junctions and can be local or global; drive-letter and DOS-device mappings must come from known namespace links, not arbitrary textual replacement; hidden Sandboxie NT box roots may be projected to the configured caller-visible DOS box root; MUP NT paths may be projected to UNC-like paths; generic NT device paths must not be rewritten to Win32 device paths without a proven DOS-device mapping; the disabled device fallback remains disabled; this SREV changes comments and proof only. |
| Topology | `\??\C:\... -> strip prefix`; `\Device\Mup\server\share\... -> UNC-like suffix`; `Dll_BoxFilePath -> Dll_BoxFileDosPath`; known drive/UNC mappings route through `File_GetDriveForPath` / `File_GetDriveForUncPath`; unmapped `\Device\...` paths return `FALSE` rather than inventing a `\\.\` path. |
| Logic Risk | The old comments blurred a valid Sandboxie presentation mapping with a disabled generic device fallback. Enabling the fallback would cross from path presentation into device namespace policy and expose arbitrary NT device paths through a Win32 device prefix that is not guaranteed to be equivalent. |
| Official Shape | Microsoft documents NT and Win32 namespaces separately, with device objects under `\Device` and Win32 exposure through symbolic links in `Global??`. Microsoft documents MS-DOS device names as object-namespace junctions. `QueryDosDevice` queries those junctions and explains that MS-DOS path conversion uses them to map drive letters and DOS devices. Microsoft also documents local and global MS-DOS device namespaces. |
| Fix | Comment-only source clarification. The hidden box-root comment now names the Sandboxie DOS-root projection. The disabled `\Device\` fallback comment now states that generic NT-device to Win32-device conversion is not legal here and remains disabled because it is a known crash-handler compatibility trap. No behavior changed. |
| Acceptance Gate | `docs/plan/check-srev-276.py` validates the draft-07 schema, official references, `SbieDll_TranslateNtToDosPath` owner block, hidden box-root mapping, drive/UNC mapping, disabled `\Device\` fallback, stale workaround/fixme wording removal, and ledger fragment; `docs/plan/check-srev-276.sh` is the targeted wrapper. Runtime gate: Windows path-presentation matrix covering `\??\` DOS paths, MUP/UNC paths, hidden box-root DOS projection, drive-letter volume paths, unmapped NT `\Device\` paths, and the Chrome crash-handler path that motivated keeping the generic device fallback disabled. |
