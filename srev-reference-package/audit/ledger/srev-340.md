---
kind: srev-ledger-entry
id: SREV-340
title: Syscall GetNextProcess Fallback Topology
status: patched-comment-topology-after-official-obcallback-process-rights-handle-reference-review-no-behavior-change
owner: Sandboxie/core/drv/syscall_open.c
spec: docs/plan/srev-340-syscall-getnextprocess-fallback-topology.md
schema: docs/plan/srev-340-syscall-getnextprocess-fallback-topology.schema.json
checker: docs/plan/check-srev-340.py
runtime_gate: Windows NtGetNextProcess matrix for ObCallbacks on off denied outside-box writable handles accepted same-box handles end-of-enumeration invalid output pointer and handle leaks
---

### SREV-340: Syscall GetNextProcess Fallback Topology

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | patched comment/topology after official ObCallback, process-rights, and handle-reference review; no behavior change |
| Evidence | `Syscall_GetNextProcess` had a stale `ToDo: make this syscall work` comment despite an existing fallback loop. When `Obj_CallbackInstalled` is true, the code allows native dispatch. Otherwise it redirects the output handle through the temporary TLS slot, invokes the native syscall, restores the slot, closes each rejected old enumeration handle, references the returned process object, checks it with `Thread_CheckObject_Common`, loops on denied processes, and writes accepted handles through `Syscall_WriteRestoredHandleToUser`. |
| Data | `Syscall_GetNextProcess`, `Obj_CallbackInstalled`, `Syscall_Invoke`, `Syscall_ReplaceTargetHandle`, `Syscall_RestoreTargetHandle`, `OldHandle`, `NewHandle`, `ObReferenceObjectByHandle`, `*PsProcessType`, `Thread_CheckObject_Common`, `DesiredAccess`, `NtClose`, `user_args[0]`, `user_args[4]`, `Syscall_WriteRestoredHandleToUser`, and SREV-045. |
| Schema | `SYSCALL_GETNEXTPROCESS_FALLBACK_TOPOLOGY` says `Syscall_GetNextProcess` owns the fallback process-handle filtering loop only when `Obj_CallbackInstalled` is false; when callbacks are installed, native dispatch is allowed because process-handle access is filtered by object callbacks; the fallback redirects the output handle through the temporary TLS slot before native dispatch; rejected outside-box process handles are closed before the next enumeration attempt; accepted process handles are returned through `Syscall_WriteRestoredHandleToUser`; no public Microsoft Learn `NtGetNextProcess` DDI page was found, so the syscall ABI remains a Windows runtime gate; this SREV changes comments and proof only. |
| Topology | `Obj_CallbackInstalled -> Syscall_Invoke`; otherwise `Syscall_ReplaceTargetHandle(&user_args[4], TRUE) -> Syscall_Invoke -> Syscall_RestoreTargetHandle -> close previous rejected enumeration handle -> ObReferenceObjectByHandle(NewHandle, *PsProcessType) -> Thread_CheckObject_Common(proc, ProcessObject, DesiredAccess, TRUE, FALSE) -> denied: user_args[0] = NewHandle; goto next -> accepted: Syscall_WriteRestoredHandleToUser(UserHandlePtr, NewHandle, orig_status)`. |
| Logic Risk | The stale TODO made an existing fallback look unimplemented. The unresolved part is not "write some code"; it is the private `NtGetNextProcess` ABI and runtime enumeration matrix. Rewriting the loop without that matrix could break rejected-handle closure or the restored-handle ownership boundary already covered by SREV-045. |
| Official Shape | Microsoft documents `ObRegisterCallbacks` as registering callbacks for thread, process, and desktop handle operations; `OB_PRE_CREATE_HANDLE_INFORMATION.DesiredAccess` as the access to grant, with callbacks allowed to remove but not add listed rights; process access rights including writable and duplication rights; and `ObReferenceObjectByHandle` as validating a handle for an object type and returning a referenced object pointer. No public Microsoft Learn `NtGetNextProcess` DDI page was found during this SREV. |
| Fix | Comment-only source clarification. The source now names SREV-340 and states that, without object callbacks, Sandboxie enumerates with `NtGetNextProcess`, closes each rejected outside-box process handle before trying the next one, and keeps the syscall ABI as a runtime-only gate. No loop condition, handle close, object reference, access check, writeback, or callback-bypass behavior changed. |
| Acceptance Gate | `docs/plan/check-srev-340.py` validates the draft-07 schema, official references, public-doc gap statement for `NtGetNextProcess`, ObCallback direct native path, fallback loop topology, rejected-handle close, process-object reference, `Thread_CheckObject_Common` access check, SREV-045 adjacency, stale TODO removal, combined ledger entry, and split ledger fragment; `docs/plan/check-srev-340.sh` is the targeted wrapper. Runtime gate: Windows VM matrix for `NtGetNextProcess` with `Obj_CallbackInstalled` on/off, denied outside-box writable process handles, accepted same-box handles, end-of-enumeration status, invalid/racing output pointer from SREV-045, and handle-leak observation while repeatedly skipping denied processes. |
