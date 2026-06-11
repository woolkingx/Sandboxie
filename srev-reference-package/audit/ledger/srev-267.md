---
kind: srev-ledger-entry
id: SREV-267
title: File ARM64EC NtOpenFile Bypass Comment Owner
status: patched-comment-topology-after-srev-054-range-gate-review-no-behavior-change
owner: Sandboxie/core/dll/file.c
spec: docs/plan/srev-267-file-arm64ec-ntopenfile-bypass-comment-owner.md
schema: docs/plan/srev-267-file-arm64ec-ntopenfile-bypass-comment-owner.schema.json
checker: docs/plan/check-srev-267.py
runtime_gate: Inherited SREV-054 ARM64EC xtajit64.dll inside/outside image range runtime proof
---

### SREV-267: File ARM64EC NtOpenFile Bypass Comment Owner

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | patched comment/topology after SREV-054 range-gate review; no behavior change |
| Evidence | `File_NtOpenFile` has an ARM64EC-only bypass for calls whose return address is inside `xtajit64.dll`. The old source comment said `TODO: Fix-Me` and described the observed `__chkstk_arm64ec` stack overflow, but did not name the owner or the gate that makes the direct `NtOpenFile` call legal. |
| Data | `File_NtOpenFile`, `_ReturnAddress()`, `Dll_xtajit64`, `Dll_xtajit64_End`, `File_NtCreateFileImpl`, and the direct `__sys_NtOpenFile` fallback. |
| Schema | `FILE_ARM64EC_NTOPENFILE_BYPASS_COMMENT_OWNER` says the ARM64EC direct `NtOpenFile` path is a compatibility bypass, not the normal Sandboxie file-policy route; SREV-054 owns the executable range gate; the bypass is legal only when the caller return address is inside the SREV-054 half-open `xtajit64.dll` image range; stale `TODO` / `Fix-Me` wording must not remain on this bypass; this SREV changes comments and proof only, while behavior remains owned by SREV-054. |
| Topology | `ARM64EC caller return address -> SREV-054 xtajit64.dll half-open image range gate -> direct NtOpenFile compatibility bypass -> otherwise normal File_NtCreateFileImpl policy path`. |
| Logic Risk | A stale TODO makes future changes likely to attack the wrong problem: removing or broadening the bypass without first reproving the SREV-054 return-address gate and ARM64EC stack-overflow runtime behavior. The topology owner must be visible at the source line where the bypass decision is made. |
| Official Shape | SREV-054 records Microsoft `GetModuleHandleW` and PE `SizeOfImage` references. The local legal gate is the SREV-054 half-open loaded-image range. |
| Fix | Comment-only source clarification. The source now names SREV-267 and states that SREV-054 owns the ARM64EC compatibility bypass and half-open image range. No behavior changed. |
| Acceptance Gate | `docs/plan/check-srev-267.py` validates the draft-07 schema, official-reference inheritance from SREV-054, source comment owner, removal of the stale TODO/Fix-Me wording from the bypass block, direct `NtOpenFile` bypass containment, and the ledger fragment; `docs/plan/check-srev-267.sh` is the targeted wrapper. Runtime gate is inherited from SREV-054. |
