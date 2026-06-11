---
kind: srev-ledger-entry
id: SREV-070
title: Handle Close Handler Lifetime
status: patched-source-level-after-local-handle-close-handler-schema-analysis-needs-wind
owner: Sandboxie/core/dll/handle.h
spec: docs/plan/srev-070-handle-close-handler-lifetime.md
schema: docs/plan/srev-070-handle-close-handler-lifetime.schema.json
checker: docs/plan/check-srev-070.py
runtime_gate: "key/file/IPC merge unregister paths do not leak handler nodes, future `pParams` callers receive the stored param, duplicate-handle close-handler propagation remains compatible with existing null-param callers"
---
### SREV-070: Handle Close Handler Lifetime

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after local handle close-handler schema analysis; needs Windows handle-lifetime runtime proof |
| Evidence | `Sandboxie/core/dll/handle.h` defines `Handle_UnRegisterHandler(..., void** pParams)`, making `pParams` an optional caller output slot. `Sandboxie/core/dll/handle.c` allocates `HANDLE_HANDLER` nodes in `Handle_RegisterHandler` and frees remaining nodes in `Handle_ExecuteCloseHandler`. Before this patch, register initialized the allocated node without checking `Dll_Alloc`, unregister assigned `pParams = handler->Param` instead of `*pParams = handler->Param`, and unregister removed nodes without freeing them. |
| Data | `HANDLE_STATE.CloseHandlers`, `HANDLE_HANDLER` allocation, callback `Param`, optional `pParams` output slot, `List_Remove`, and `Dll_Free`. |
| Schema | `HANDLE_CLOSE_HANDLER_LIFETIME` says the handle module owns each `HANDLE_HANDLER` node from successful registration until explicit unregister or close execution. Register may initialize a node only after allocation succeeds; unregister must write output through `*pParams` when requested and release removed nodes with `Dll_Free`. |
| Topology | `Handle_RegisterHandler` inserts owned close-handler nodes into `HANDLE_STATE`; `Handle_UnRegisterHandler` and `Handle_ExecuteCloseHandler` are the only legal node-lifetime exits. |
| Logic Risk | A local handler-lifetime owner should not leak every explicitly unregistered handler node or lose a caller-requested output parameter. Allocation failure should also fail closed before list-node initialization. |
| Official Shape | This is an internal Sandboxie API, so `docs/plan/srev-070-handle-close-handler-lifetime.md` records the local header/source boundary rather than an external Microsoft API. `docs/plan/srev-070-handle-close-handler-lifetime.schema.json` records the JSON Schema draft-07 local `HANDLE_CLOSE_HANDLER_LIFETIME` contract. |
| Fix | `Handle_RegisterHandler` now returns `FALSE` if handler-node allocation fails. `Handle_UnRegisterHandler` now writes `*pParams = handler->Param`, removes the node, and frees it with `Dll_Free(handler)`. |
| Acceptance Gate | `docs/plan/check-srev-070.py` validates the draft-07 schema, local header boundary, register allocation gate, unregister output-slot write, node removal/free, execute-close free path, and ledger entry; `docs/plan/check-srev-070.sh` is the matrix wrapper. Windows gate: key/file/IPC merge unregister paths do not leak handler nodes, future `pParams` callers receive the stored param, duplicate-handle close-handler propagation remains compatible with existing null-param callers. |
