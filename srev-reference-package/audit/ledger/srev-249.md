---
kind: srev-ledger-entry
id: SREV-249
title: Digital Guardian Comment Topology
status: patched-comment-topology-after-official-getmodulehandle-and-dllmain-review-no-behavior-change
owner: Sandboxie/core/dll/dllmain.c and Sandboxie/core/dll/file.c
spec: docs/plan/srev-249-digitalguardian-comment-topology.md
schema: docs/plan/srev-249-digitalguardian-comment-topology.schema.json
checker: docs/plan/check-srev-249.py
runtime_gate: No runtime gate required for comment-only clarification; earlier behavior-changing SREV rows own Windows compatibility proof
---

### SREV-249: Digital Guardian Comment Topology

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | patched comment/topology after official `GetModuleHandleA` and `DllMain` review; no behavior change |
| Evidence | SREV-088 already classified `Dll_DigitalGuardian` as module-presence evidence. `dllmain.c` seeds the flag through `GetModuleHandleA("DgApi64.dll")` / `GetModuleHandleA("DgApi.dll")`; `ldr.c` wires `DigitalGuardian_Init`; `file.c` consumes the flag for Digital Guardian file-policy compatibility. The remaining anonymous `$Workaround$ - 3rd party fix` labels in `dllmain.c` and `file.c` hid the same topology already documented by SREV-088. |
| Data | `Dll_DigitalGuardian`, `GetModuleHandleA("DgApi64.dll")`, `GetModuleHandleA("DgApi.dll")`, `DigitalGuardian_Init`, `DllMain`, `FILE_DELETE_ON_CLOSE`, `PATH_IS_WRITE`, `PATH_IS_CLOSED`, `NtQueryFullAttributesFile`, and SREV-088 module-presence topology. |
| Schema | `DIGITALGUARDIAN_COMMENT_TOPOLOGY` says `Dll_DigitalGuardian` is module-presence evidence rather than module ownership; `DllMain` may seed the flag only when the Digital Guardian DLL is already mapped in the current process; `DigitalGuardian_Init` updates the same flag when the loader observes the module later; `file.c` owns Digital Guardian file-policy compatibility branches; the comment clarification must not change detection, loader callback, file-policy branch conditions, or return values. |
| Topology | Process attach path is `DllMain(DLL_PROCESS_ATTACH)`, `GetModuleHandleA(DgApi64.dll / DgApi.dll)`, then `Dll_DigitalGuardian`. Loader callback path is `ldr.c` module table, `DigitalGuardian_Init(hModule)`, then `Dll_DigitalGuardian`. File-policy path is `file.c` delete-on-close and true-path attribute checks reading the flag to choose the Digital Guardian compatibility branch or direct true-file query. |
| Logic Risk | The old labels made one cross-file module-presence topology look like unrelated third-party residue. That increases the chance of a future patch treating the `HMODULE` as a lifetime-owned reference, removing the early seed while keeping the loader callback, or altering the file-policy branch without understanding why the module flag exists. |
| Official Shape | `docs/plan/srev-249-digitalguardian-comment-topology.md` records Microsoft `GetModuleHandleA` and `DllMain` references. `docs/plan/srev-249-digitalguardian-comment-topology.schema.json` records the JSON Schema draft-07 local `DIGITALGUARDIAN_COMMENT_TOPOLOGY` contract. |
| Fix | Comment-only source clarification. `dllmain.c` now names `Dll_DigitalGuardian` as a module-presence flag and explains the early seed. `file.c` now names the Digital Guardian delete-on-close branch, true-path attribute-query branch, and loader callback role. |
| Acceptance Gate | `docs/plan/check-srev-249.py` validates the draft-07 schema, official reference links, SREV-088 adjacency, `GetModuleHandleA` seed shape, `ldr.c` callback shape, `file.c` policy consumers, removal of stale anonymous labels from the Digital Guardian source sites, and the ledger fragment; `docs/plan/check-srev-249.sh` is the targeted wrapper. Runtime gate: not required for this comment-only clarification. Existing Digital Guardian runtime behavior remains a Windows compatibility gate owned by the earlier behavior-changing SREV rows. |
