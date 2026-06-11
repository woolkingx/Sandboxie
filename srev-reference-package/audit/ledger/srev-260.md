---
kind: srev-ledger-entry
id: SREV-260
title: DLL Hook Unity Runtime Gate Wording
status: patched-comment-topology-after-srev-246-nop-padding-review-no-behavior-change
owner: Sandboxie/core/dll/dllhook.c
spec: docs/plan/srev-260-dllhook-unity-runtime-gate-wording.md
schema: docs/plan/srev-260-dllhook-unity-runtime-gate-wording.schema.json
checker: docs/plan/check-srev-260.py
runtime_gate: Inherited from SREV-246 for any future NOP-padding behavior patch
---

### SREV-260: DLL Hook Unity Runtime Gate Wording

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | patched comment/topology after SREV-246 NOP-padding review; no behavior change |
| Evidence | SREV-246 already classified the disabled NOP-padding block as a detour span and trampoline byte-count owner boundary. The remaining source wording still used a historical symptom phrase about Unity breakage. This SREV removes the symptom wording and names the gate directly. |
| Data | `SbieDll_Hook_x86`, disabled NOP padding, `HookTramp` `ByteCount`, detour write span, and Unity runtime gate. |
| Schema | `DLLHOOK_UNITY_RUNTIME_GATE_WORDING` says SREV-246 owns the disabled NOP-padding boundary; the source comment must name the Unity runtime gate rather than symptom-only breakage wording; this SREV does not change hook bytes, NOP-padding state, page protection, instruction-cache flushing, trampoline generation, or runtime policy. |
| Topology | `SbieApi_HookTramp ByteCount -> disabled NOP-padding span -> future behavior requires Unity runtime gate`. |
| Logic Risk | Historical breakage wording can be mistaken for folklore. The actionable rule is the runtime gate: do not enable NOP padding until the hook matrix and Unity runtime proof exist. |
| Official Shape | SREV-260 inherits SREV-246's executable-code owner/span contract. No new Windows API shape is introduced. |
| Fix | Comment-only source clarification. The source now says the write span needs a Unity runtime gate. No behavior changed. |
| Acceptance Gate | `docs/plan/check-srev-260.py` validates the draft-07 schema, source comment, removal of the symptom-only breakage wording, preservation of the disabled NOP block, SREV-246 adjacency, and the ledger fragment; `docs/plan/check-srev-260.sh` is the targeted wrapper. Runtime gate is inherited from SREV-246 for any future behavior patch. |
