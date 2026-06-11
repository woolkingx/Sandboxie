---
kind: srev-ledger-entry
id: SREV-298
title: Handle Propagated Close Handler Param Gate
status: patched-source-level-local-propagation-contract-needs-windows-runtime-proof
owner: Sandboxie/core/dll/handle.c
spec: docs/plan/srev-298-handle-propagated-close-handler-param-gate.md
schema: docs/plan/srev-298-handle-propagated-close-handler-param-gate.schema.json
checker: docs/plan/check-srev-298.py
runtime_gate: Windows duplicate-handle smoke proving File_NotifyRecover propagation and bPropagate with non-null Param rejection
---

### SREV-298: Handle Propagated Close Handler Param Gate

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | patched source-level local propagation contract; needs Windows runtime proof |
| Evidence | `HANDLE_HANDLER` stores `Close`, `Param`, and `bPropagate`. `Handle_SetupDuplicate` is called after a same-process duplicate succeeds and propagates close-handler metadata to the new handle with `Handle_RegisterHandler(NewFileHandle, handler->Close, NULL, TRUE)`. The old source comment already admitted `bPropagate` was incompatible with `Param`. Current propagated source registration is `Handle_RegisterHandler(FileHandle, File_NotifyRecover, NULL, TRUE)`. |
| Data | `HANDLE_STATE.CloseHandlers`, `HANDLE_HANDLER.Close`, `HANDLE_HANDLER.Param`, `HANDLE_HANDLER.bPropagate`, `Handle_RegisterHandler`, `Handle_SetupDuplicate`, `secure.c` duplicate success path, `File_NotifyRecover`, `DuplicateHandle`, and `ZwDuplicateObject`. |
| Schema | `HANDLE_PROPAGATED_CLOSE_HANDLER_PARAM_GATE` says `Handle_RegisterHandler` owns admission of `Close`, `Param`, and `bPropagate` metadata; propagated close handlers are legal only when `Param` is `NULL` until a duplicate-param owner exists; `Handle_SetupDuplicate` copies propagated close handlers with `NULL` `Param` only; SREV-070 owns `HANDLE_HANDLER` node lifetime; this SREV does not change current `File_NotifyRecover` propagation behavior. |
| Topology | `DuplicateHandle / NtDuplicateObject -> OS handle table entry duplicate -> secure.c calls Handle_SetupDuplicate for same-process target -> handle.c propagates only metadata with local duplicate contract`; `Handle_RegisterHandler -> admission gate for bPropagate/Param compatibility`. |
| Logic Risk | The previous code silently converted any propagated handler's `Param` to `NULL` during duplicate setup. That is safe for the current file-recovery caller, but it would corrupt a future propagated handler that expects a non-null parameter. The local contract should fail closed until a real duplicate-param owner exists. |
| Official Shape | Microsoft documents `DuplicateHandle` and `ZwDuplicateObject` as OS handle-table duplicate operations. They do not duplicate Sandboxie private `HANDLE_STATE.CloseHandlers` metadata; that metadata is local to `handle.c`. |
| Fix | `Handle_RegisterHandler` now rejects `bPropagate && Params` before inserting a handler node. The `HANDLE_HANDLER.bPropagate` source comment now records the SREV-298 contract. The stale duplicate-registration todo comment was replaced with a behavior comment. No existing propagated caller changes behavior because current propagated registration uses `Param == NULL`. |
| Acceptance Gate | `docs/plan/check-srev-298.py` validates the draft-07 schema, official references, source admission gate, duplicate setup's continued `NULL` param propagation, current propagated caller shape, stale todo removal, SREV-070 adjacency, combined ledger entry, and split ledger fragment; `docs/plan/check-srev-298.sh` is the targeted wrapper. Runtime gate: Windows duplicate-handle smoke proving file recovery metadata still propagates for `File_NotifyRecover` and a negative unit/runtime probe proving `bPropagate && Params` fails registration. |
