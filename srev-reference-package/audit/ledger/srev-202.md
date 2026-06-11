---
kind: srev-ledger-entry
id: SREV-202
title: XP Object Type Hook Contract
status: patched-source-level-after-official-object-manager-shape-review-needs-windows-runtime-proof
owner: Sandboxie/core/drv/obj_xp.c
spec: docs/plan/srev-202-xp-object-type-hook-contract.md
schema: docs/plan/srev-202-xp-object-type-hook-contract.schema.json
checker: docs/plan/check-srev-202.py
runtime_gate: Windows XP / Server 2003 compatible driver build or historical target build plus File, Device, and Key parse-procedure hook initialization smoke
---

### SREV-202: XP Object Type Hook Contract

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official object-manager shape review; needs Windows runtime proof |
| Evidence | `Sandboxie/core/drv/obj_xp.c` was the top unnamed reviewable core file after SREV-201. It owns the Windows XP / Server 2003 object-type parse-procedure hook path. Before this fix, `Obj_HookAnyProc` built `\ObjectTypes\<TypeName>` with unchecked `wcscpy` / `wcscat`, dereferenced output pointers without an explicit helper contract, accepted a null replacement procedure, and used `ProcOffset` without proving it addressed a complete pointer-sized slot inside the local `OBJECT_TYPE.TypeInfo` projection before reading and publishing the hook pointer. |
| Data | `Obj_HookParseProc`, `Obj_HookAnyProc`, `Obj_BuildObjectTypeName`, `TypeName`, `NewProc`, `OldProc`, `HookEntry`, `ProcOffset`, `OBJECT_TYPE.TypeInfo`, `OBJECT_TYPE_INITIALIZER.ParseProcedure`, `ObOpenObjectByName`, `ObReferenceObjectByHandle`, `Process_BuildHookEntry`, `KeMemoryBarrier`, and `InterlockedExchangePointer`. |
| Schema | `XP_OBJECT_TYPE_HOOK_CONTRACT` says the object-type path is built through a bounded owner helper; `TypeName`, `NewProc`, `OldProc`, and `pHookEntry` are required before object open/reference/publish; `ProcOffset` must point to a pointer-sized slot inside the local `TypeInfo` projection before `OldProc` is read and before hook publication; `Process_BuildHookEntry` success gates `InterlockedExchangePointer`; and the private XP object-type layout remains a local compatibility dependency rather than an official API. |
| Topology | Legal flow is `File/Key XP init -> Obj_HookParseProc -> Obj_HookAnyProc input gate -> bounded \ObjectTypes\<TypeName> path -> ObOpenObjectByName -> ObReferenceObjectByHandle -> ProcOffset inside TypeInfo pointer slot -> Process_BuildHookEntry -> KeMemoryBarrier -> InterlockedExchangePointer`. |
| Logic Risk | Current callers pass small constants and valid output pointers, so this was a latent helper-boundary defect rather than a proven current overflow. Without the owner-local gates, future object-type additions or failed caller paths could turn the unchecked path build, output pointer writes, or offset calculation into a kernel init crash or hook-publish corruption. |
| Official Shape | `docs/plan/srev-202-xp-object-type-hook-contract.md` records Microsoft `RtlInitUnicodeString`, `InitializeObjectAttributes`, `ObReferenceObjectByHandle`, object opacity, and `InterlockedExchangePointer` references. `docs/plan/srev-202-xp-object-type-hook-contract.schema.json` records the JSON Schema draft-07 local `XP_OBJECT_TYPE_HOOK_CONTRACT` contract. |
| Fix | `obj_xp.c` now rejects null `TypeName`, `NewProc`, `OldProc`, and `pHookEntry`; builds `\ObjectTypes\<TypeName>` through `Obj_BuildObjectTypeName`; rejects `ProcOffset` values that cannot address a complete `ULONG_PTR` inside `object->TypeInfo`; and preserves the successful XP parse-procedure hook publish topology. |
| Acceptance Gate | `docs/plan/check-srev-202.py` validates the draft-07 schema, official references, source-level input gates, bounded path builder, stale unchecked `wcscpy` / `wcscat` removal, offset gate before hook pointer read/publish, and split ledger fragment; `docs/plan/check-srev-202.sh` is the targeted wrapper. Runtime/build gate: Windows XP / Server 2003 compatible driver build or historical target build plus File, Device, and Key parse-procedure hook initialization smoke. |
