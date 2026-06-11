---
kind: srev-ledger-entry
id: SREV-258
title: Custom SYSFER Comment Owner
status: patched-comment-topology-after-srev-055-entrypoint-patch-review-no-behavior-change
owner: Sandboxie/core/dll/custom.c
spec: docs/plan/srev-258-custom-sysfer-comment-owner.md
schema: docs/plan/srev-258-custom-sysfer-comment-owner.schema.json
checker: docs/plan/check-srev-258.py
runtime_gate: Inherited from SREV-055 Windows endpoint-protection compatibility proof remains required
---

### SREV-258: Custom SYSFER Comment Owner

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | patched comment/topology after SREV-055 entry-point patch review; no behavior change |
| Evidence | SREV-055 already owns and hardens the SYSFER entry-point patch: PE signature gates, bounded entry-point span, exact `VirtualProtect` range, `FlushInstructionCache`, and protection restore. The remaining `custom.c` comment still described the patch as a generic workaround to nullify `SYSFER.DLL`. That wording hides the exact owner and can misroute future work into broad third-party patching instead of the already documented PE entry-point boundary. |
| Data | `Custom_SYSFER_DLL`, `SYSFER.DLL`, PE DOS/NT headers, `AddressOfEntryPoint`, `SizeOfImage`, four-byte `mov al, 1; ret` patch, `VirtualProtect`, `FlushInstructionCache`, and SREV-055. |
| Schema | `CUSTOM_SYSFER_COMMENT_OWNER` says SREV-055 owns the executable-code patch boundary for `SYSFER.DLL`; the source comment must name the bounded entry-point patch owner rather than a generic workaround; this SREV does not change PE validation, patch bytes, page protection, instruction-cache coherency, or Symantec compatibility behavior. |
| Topology | `SYSFER.DLL load -> valid PE image and entry-point span -> SREV-055 bounded entry-point patch owner -> exact four-byte patch plus instruction-cache coherency`. |
| Logic Risk | Generic workaround wording obscures the fact that the code is an executable-code mutation with strict PE and cache-coherency gates. Future patches should extend or revise SREV-055's owner boundary rather than treating this as anonymous third-party residue. |
| Official Shape | `docs/plan/srev-258-custom-sysfer-comment-owner.md` inherits Microsoft PE, `VirtualProtect`, and `FlushInstructionCache` references from SREV-055. `docs/plan/srev-258-custom-sysfer-comment-owner.schema.json` records the JSON Schema draft-07 local `CUSTOM_SYSFER_COMMENT_OWNER` contract. |
| Fix | Comment-only source clarification. The source now says SREV-055 owns the bounded entry-point patch for the `SYSFER.DLL` load path. No behavior changed. |
| Acceptance Gate | `docs/plan/check-srev-258.py` validates the draft-07 schema, SREV-055 adjacency, source comment, removal of the stale generic workaround wording, unchanged patch behavior evidence, and the ledger fragment; `docs/plan/check-srev-258.sh` is the targeted wrapper. Runtime gate is inherited from SREV-055: Windows endpoint-protection compatibility proof remains required for behavior closure. |
