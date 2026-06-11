---
kind: srev-ledger-entry
id: SREV-246
title: DLL Hook Unity NOP Padding Boundary
status: patched-comment-topology-after-official-executable-code-review-no-behavior-change
owner: Sandboxie/core/dll/dllhook.c
spec: docs/plan/srev-246-dllhook-unity-nop-padding-boundary.md
schema: docs/plan/srev-246-dllhook-unity-nop-padding-boundary.schema.json
checker: docs/plan/check-srev-246.py
runtime_gate: Future NOP-padding behavior patch needs Windows hook matrix plus Unity runtime proof
---

### SREV-246: DLL Hook Unity NOP Padding Boundary

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | patched comment/topology after official executable-code review; no behavior change |
| Evidence | `Sandboxie/core/dll/dllhook.c` had a disabled NOP-padding block after the `SbieDll_Hook_x86` detour write path with the comment `ToDo: why does this break unity games`. The active code writes a source-entry detour, restores protection, and flushes the instruction cache. `hook_tramp.c` owns moved-instruction `ByteCount` and trampoline copy layout. |
| Data | `SbieDll_Hook_x86`, `SbieApi_HookTramp`, `Hook_Tramp_CountBytes`, `Hook_Tramp_Copy`, `ByteCount`, `UsedCount`, source-function detour bytes, trampoline bytes, x86 `E9 rel32`, x64 `FF 25 rip+disp32`, Windows 10 `48 E9`, NOP padding, page-protection restore, and instruction-cache flush. |
| Schema | `DLLHOOK_UNITY_NOP_PADDING_BOUNDARY` says `hook_tramp.c` owns copied-instruction byte counting; `dllhook.c` owns only the active detour envelope it writes at the source function entry; the entry detour transfers normal control flow before any tail bytes execute; NOP-padding from `UsedCount` to `ByteCount` changes the writable code span and compatibility surface; the old Unity breakage is runtime compatibility evidence, not proof that NOP padding is impossible; a future NOP-padding patch must first publish a checked `ByteCount` / `UsedCount` contract from the trampoline owner and must run a Windows hook runtime matrix including Unity; this SREV does not change detour bytes, trampoline generation, page protection, cache flushing, or hook policy. |
| Topology | Current legal path is `SbieApi_HookTramp` copies enough source instructions into a trampoline, `SbieDll_Hook_x86` writes the entry detour envelope, remaining source bytes are not part of normal entry control flow, page protection is restored, `FlushInstructionCache` crosses the execution boundary, and the caller receives the trampoline pointer. The disabled path would connect HookTramp `ByteCount` to `dllhook` `UsedCount`, write NOPs across the moved instruction tail, and expand the executable mutation span. |
| Logic Risk | The original TODO looked like a simple cleanup. The real owner issue is that `ByteCount` comes from the trampoline builder, while the source detour writer currently has no active checked contract saying which tail bytes are safe to overwrite for every accepted instruction shape and third-party detour envelope. Enabling NOP padding without that contract would reintroduce the known Unity compatibility risk. |
| Official Shape | `docs/plan/srev-246-dllhook-unity-nop-padding-boundary.md` records Intel instruction-set references plus Microsoft `VirtualProtect` and `FlushInstructionCache` references. `docs/plan/srev-246-dllhook-unity-nop-padding-boundary.schema.json` records the JSON Schema draft-07 local `DLLHOOK_UNITY_NOP_PADDING_BOUNDARY` contract. |
| Fix | Comment-only source clarification. The disabled NOP block now states that the entry jump already owns the normal control-flow transfer and that extending the write span to HookTramp's `ByteCount` needs a Unity runtime gate. |
| Acceptance Gate | `docs/plan/check-srev-246.py` validates the draft-07 schema, official reference links, source evidence for the disabled NOP block, replacement of the old symptom-only TODO/breakage wording with the owner/span contract, `hook_tramp.c` ByteCount owner evidence, SREV-058 cache-coherency adjacency, SREV-091 detour-envelope adjacency, and the ledger fragment. Runtime gate: not required for this comment-only clarification; any future behavior patch that enables NOP padding must run Windows x86/WoW64/x64 hook smoke tests, third-party detour-envelope compatibility tests, and a Unity game launch/runtime smoke that proves no regression. |
