---
kind: srev-ledger-entry
id: SREV-342
title: Token Primary Kernel Handle Boundary
status: patched-comment-topology-after-official-object-handle-and-driver-verifier-review-no-behavior-change
owner: Sandboxie/core/drv/token.c
spec: docs/plan/srev-342-token-primary-kernel-handle-boundary.md
schema: docs/plan/srev-342-token-primary-kernel-handle-boundary.schema.json
checker: docs/plan/check-srev-342.py
runtime_gate: Windows driver build and Driver Verifier miscellaneous checks on Windows 7 10 11 for primary-token replacement kernel handles cleanup and ProcessAccessToken failures
---

### SREV-342: Token Primary Kernel Handle Boundary

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | patched comment/topology after official object-handle and Driver Verifier review; no behavior change |
| Evidence | `Token_AssignPrimary` opens `TokenObject` with `ObOpenObjectByPointer(... OBJ_KERNEL_HANDLE ..., KernelMode, &TokenHandle)`, passes that handle to `Token_AssignPrimaryHandle`, and closes it after the assignment attempt. `Token_AssignPrimaryHandle` opens the process object with the same kernel-handle shape, places the token handle in `PROCESS_ACCESS_TOKEN.Token`, calls `ZwSetInformationProcess(ProcessAccessToken)`, then closes the process handle. The old comment only said Windows 7 Driver Verifier would crash if the token handle was not a kernel handle. |
| Data | `Token_AssignPrimary`, `Token_AssignPrimaryHandle`, `TokenObject`, `TokenKernelHandle`, `ProcessObject`, `ProcessHandle`, `TokenHandle`, `ObOpenObjectByPointer`, `OBJ_KERNEL_HANDLE`, `KernelMode`, `PROCESS_ACCESS_TOKEN`, `info.Token`, `info.Thread`, `ZwSetInformationProcess`, `ProcessAccessToken`, `ZwClose`, Driver Verifier miscellaneous checks, and Windows 7. |
| Schema | `TOKEN_PRIMARY_KERNEL_HANDLE_BOUNDARY` says `Token_AssignPrimary` owns conversion from token object pointer to kernel-only token handle; `Token_AssignPrimaryHandle` consumes a kernel-only token handle in `PROCESS_ACCESS_TOKEN`; both token and process object pointers are opened with `OBJ_KERNEL_HANDLE` and `KernelMode`; the `ProcessAccessToken` private ABI shape remains a Windows runtime gate; Driver Verifier kernel-handle checks are the verification owner for the Windows 7 crash note; successful and failed paths close the opened kernel handles; this SREV changes comments and proof only. |
| Topology | `TokenObject -> ObOpenObjectByPointer(OBJ_KERNEL_HANDLE, KernelMode) -> TokenHandle -> Token_AssignPrimaryHandle -> ProcessObject -> ObOpenObjectByPointer(OBJ_KERNEL_HANDLE, KernelMode) -> ProcessHandle -> PROCESS_ACCESS_TOKEN { TokenKernelHandle, NULL thread } -> ZwSetInformationProcess(ProcessAccessToken) -> restore PrimaryTokenFrozen -> ZwClose(ProcessHandle) -> ZwClose(TokenHandle)`. |
| Logic Risk | The old comment was accurate but too narrow. It framed the invariant as a Windows 7 Driver Verifier crash avoidance note, not as a handle-owner boundary. Future edits could pass a user-visible token handle into `Token_AssignPrimaryHandle` or move token-handle creation away from the `OBJ_KERNEL_HANDLE` edge without noticing that `ProcessAccessToken` consumes a kernel-only handle in this local topology. |
| Official Shape | Microsoft documents `ObOpenObjectByPointer` as returning an object handle and requiring `OBJ_KERNEL_HANDLE` when the caller is not running in the system process context; the returned handle must be closed with `ZwClose`. Microsoft documents `ObReferenceObjectByHandle` and Driver Verifier's Windows 7+ kernel/user handle checks, including bug checks for invalid kernel-handle references. Microsoft documents `PROCESS_SET_INFORMATION` as a process right for setting process information. No public Microsoft Learn `ZwSetInformationProcess(ProcessAccessToken)` / `PROCESS_ACCESS_TOKEN` ABI page was found during this SREV. |
| Fix | Comment-only source clarification. The source now names SREV-342 and says `ProcessAccessToken` consumes a kernel-only token handle; `Token_AssignPrimary` opens `TokenObject` with `OBJ_KERNEL_HANDLE`; and that owner boundary must stay paired with `ZwSetInformationProcess` and Driver Verifier's kernel-handle checks. No handle attribute, access mode, process-token replacement behavior, frozen-bit handling, mitigation flag write, status logging, or close behavior changed. |
| Acceptance Gate | `docs/plan/check-srev-342.py` validates the draft-07 schema, official references, token object to `OBJ_KERNEL_HANDLE` edge, process object to `OBJ_KERNEL_HANDLE` edge, `PROCESS_ACCESS_TOKEN` consumer, `ZwClose` cleanup, stale Driver Verifier crash wording removal, combined ledger entry, and split ledger fragment; `docs/plan/check-srev-342.sh` is the targeted wrapper. Runtime gate: Windows driver build and VM matrix with Driver Verifier miscellaneous checks on Windows 7/10/11 for primary-token replacement, confirming the token and process handles stay kernel-only, rejected `ZwSetInformationProcess(ProcessAccessToken)` paths close both handles, and normal sandbox primary-token replacement still works. |
