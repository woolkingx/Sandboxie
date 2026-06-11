---
kind: srev-ledger-entry
id: SREV-335
title: IPC COM Server Classifier
status: patched-comment-topology-after-official-com-broker-boundary-review-no-behavior-change
owner: Sandboxie/core/drv/ipc.c
spec: docs/plan/srev-335-ipc-com-server-classifier.md
schema: docs/plan/srev-335-ipc-com-server-classifier.schema.json
checker: docs/plan/check-srev-335.py
runtime_gate: Windows COM activation matrix for legacy app targets parent context and negative classifier cases
---

### SREV-335: IPC COM Server Classifier

| Field | Content |
|---|---|
| Severity | [medium] |
| Status | patched comment/topology after official COM activation, local-server, and broker-boundary review; no behavior change |
| Evidence | `Ipc_InitPaths` marks a process `untouchable` when `Ipc_IsComServer` returns true. `Ipc_IsComServer` requires a forced process, an image not from inside the box, an image name in the legacy `iexplore.exe` / `wmplayer.exe` / `winamp.exe` / `kmplayer.exe` allowlist, a parent process that exists outside the sandbox, and a parent running as the system account. The old image predicate comment framed this as a generic third-party workaround. |
| Data | `Ipc_InitPaths`, `Ipc_IsComServer`, `proc->forced_process`, `proc->image_from_box`, `proc->image_name`, `MyGetParentId`, `Process_Find`, `MyIsProcessRunningAsSystemAccount`, `proc->untouchable`, `Custom_ComServer`, `SbieDll_RunSandboxed`, `ProcessServer::RunSandboxedComServer`, `comserver9.c`, `CoCreateInstance`, `CoRegisterClassObject`, and `LocalServer32`. |
| Schema | `IPC_COM_SERVER_CLASSIFIER` says `Ipc_IsComServer` owns only driver-side forced COM server classification; the classifier applies only to forced processes whose image did not come from inside the box; the image allowlist remains `iexplore.exe`, `wmplayer.exe`, `winamp.exe`, and `kmplayer.exe`; the parent process must exist, must be outside the sandbox, and must run as system account; `Ipc_InitPaths` marks a classified forced COM server process as `untouchable`; `Custom_ComServer` and SREV-256 own the brokered COM handoff topology; this SREV changes comments and proof only. |
| Topology | `out-of-sandbox COM activation -> SbieSvc forced sandboxed local-server launch -> driver process flags and parent-context classifier -> Ipc_InitPaths marks classified process untouchable -> Custom_ComServer/SbieSvc comserver9.c owns the brokered COM conversation`. Classifier path: `Ipc_IsComServer -> forced_process -> image_from_box == false -> legacy app allowlist -> parent exists -> parent is not sandboxed -> parent runs as system`. |
| Logic Risk | Treating the predicate as a generic workaround hides the owner split. The driver classifier could be widened or weakened as if it owned COM broker semantics, while the actual brokered handoff belongs to `Custom_ComServer`, SREV-256, `ProcessServer::RunSandboxedComServer`, and `comserver9.c`. |
| Official Shape | Microsoft documents `CoCreateInstance` as local COM object activation, `CoRegisterClassObject` as the EXE object application's registration path for class objects, and `LocalServer32` as the registry path used to launch local COM server applications. |
| Fix | Comment-only source clarification. The source now names SREV-335 and states that the image predicate is part of a driver-side forced COM server classifier for the brokered SbieSvc handoff owned by `Custom_ComServer` and SREV-256. No process flags, image allowlist, parent checks, `untouchable` behavior, service broker request, or COM conversation code changed. |
| Acceptance Gate | `docs/plan/check-srev-335.py` validates the draft-07 schema, official references, `Ipc_IsComServer` predicates, `Ipc_InitPaths` `untouchable` marker, SREV-256 `Custom_ComServer` broker adjacency, `comserver9.c` matching image allowlist, `ProcessServer::RunSandboxedComServer` forced/protected flag gate, stale workaround wording removal from the classifier block, combined ledger entry, and split ledger fragment; `docs/plan/check-srev-335.sh` is the targeted wrapper. Runtime gate: Windows COM activation matrix for the four legacy application targets, parent SYSTEM context, out-of-box parent launch, sandboxed parent negative case, and non-allowlisted forced-process negative case. |
