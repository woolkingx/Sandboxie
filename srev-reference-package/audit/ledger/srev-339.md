---
kind: srev-ledger-entry
id: SREV-339
title: Syscall OpenThread WOW64 ClientId Probe
status: patched-source-level-after-official-openthread-thread-rights-wow64-probeforread-review-needs-windows-runtime-proof
owner: Sandboxie/core/drv/syscall_open.c
spec: docs/plan/srev-339-syscall-open-thread-wow64-client-id-probe.md
schema: docs/plan/srev-339-syscall-open-thread-wow64-client-id-probe.schema.json
checker: docs/plan/check-srev-339.py
runtime_gate: Windows x64 WOW64 OpenThread smoke for host thread read-context same-box preservation outside-box downgrade null or invalid ClientId and Driver Verifier user-buffer observation
---

### SREV-339: Syscall OpenThread WOW64 ClientId Probe

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official OpenThread, thread-rights, WOW64, and ProbeForRead review; needs Windows WOW64 runtime proof |
| Evidence | `Syscall_OpenHandle` had a Windows 10 1903+ WOW64 OpenThread compatibility gate for the exact `THREAD_GET_CONTEXT | THREAD_SET_CONTEXT` access mask. It removed `THREAD_SET_CONTEXT` for null or outside-box targets, but read `ClientId->UniqueProcess` directly from the caller-supplied syscall argument pointer. The outer `Syscall_Api_Invoke` try/except could catch a fault, but the local OpenThread boundary did not prove the `CLIENT_ID` user buffer before reading it. |
| Data | `Syscall_OpenHandle`, `OpenThread`, `user_args[1]`, `user_args[3]`, `PCLIENT_ID`, `CLIENT_ID.UniqueProcess`, `THREAD_GET_CONTEXT`, `THREAD_SET_CONTEXT`, `ProbeForRead`, `GetExceptionCode`, `Process_IsSameBox`, `Syscall_Invoke`, `Syscall_CheckObject`, `Syscall_WriteRestoredHandleToUser`, SREV-045, and SREV-333. |
| Schema | `SYSCALL_OPEN_THREAD_WOW64_CLIENT_ID_PROBE` says `Syscall_OpenHandle` owns the OpenThread `THREAD_GET_CONTEXT | THREAD_SET_CONTEXT` compatibility downgrade; the downgrade applies only to that exact access mask; the caller-supplied `CLIENT_ID` pointer must be probed before reading `UniqueProcess`; `ProbeForRead` and the read must stay inside a local try/except block; invalid `CLIENT_ID` access returns the exception code before native syscall dispatch; `Process_IsSameBox` receives a captured process id, not a user pointer; this SREV does not change handle replacement, object validation, or restored-handle writeback topology. |
| Topology | `Syscall_Api_Invoke -> ProbeForRead(user_args) -> Syscall_OpenHandle -> OpenThread exact access-mask gate -> PCLIENT_ID user_args[3] -> ProbeForRead(CLIENT_ID) -> captured UniqueProcess -> Process_IsSameBox -> optional THREAD_SET_CONTEXT removal -> Syscall_Invoke -> Syscall_CheckObject -> Syscall_WriteRestoredHandleToUser`. |
| Logic Risk | The stale HACK wording made the branch look like a broad compatibility exception while hiding the user-pointer boundary. Future edits could broaden the access-mask match or read `CLIENT_ID` outside try/except. The legal route is to prove the `CLIENT_ID` buffer, capture the process id, and apply only the narrow outside-box read-context downgrade. |
| Official Shape | Microsoft documents `OpenThread` as checking requested thread access against the thread security descriptor and granting only the requested extent. Microsoft documents `THREAD_GET_CONTEXT` as read-context access and `THREAD_SET_CONTEXT` as write-context access. Microsoft documents WOW64 as a user-mode thunk layer that extracts 32-bit stack arguments and makes native system calls. Microsoft documents `ProbeForRead` as raising exceptions for invalid user buffers and requiring try/except around the probe and later accesses. |
| Fix | `Syscall_OpenHandle` now names SREV-339 and the Windows 10 1903+ WOW64 read-context gate. It probes a non-null `CLIENT_ID` pointer with `ProbeForRead(ClientId, sizeof(CLIENT_ID), sizeof(ULONG_PTR))`, captures `UniqueProcess` inside local try/except, returns `GetExceptionCode()` on probe/read exception, and passes only the captured process id to `Process_IsSameBox`. The exact access-mask match, null-target downgrade, outside-box downgrade, later handle replacement, object validation, and writeback topology remain unchanged. |
| Acceptance Gate | `docs/plan/check-srev-339.py` validates the draft-07 schema, official references, source comment ownership, exact OpenThread access-mask gate, `CLIENT_ID` probe-before-read, captured `ClientProcessId`, local exception return, `Process_IsSameBox` use, stale HACK/direct-read wording removal, SREV-045 / SREV-333 adjacency, combined ledger entry, and split ledger fragment; `docs/plan/check-srev-339.sh` is the targeted wrapper. Runtime gate: Windows x64 WOW64 smoke on Windows 10 1903+ and current Windows, covering host-thread read-context behavior, same-box OpenThread `THREAD_GET_CONTEXT|THREAD_SET_CONTEXT`, outside-box downgrade to `THREAD_GET_CONTEXT`, null/invalid `CLIENT_ID`, malformed user pointer exception status, and Driver Verifier user-buffer observation. |
