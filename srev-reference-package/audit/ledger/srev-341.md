---
kind: srev-ledger-entry
id: SREV-341
title: Thread Change Notify Token Status Sentinel
status: patched-comment-topology-after-official-ntsetinformationthread-impersonation-token-privilege-review-no-behavior-change
owner: Sandboxie/core/drv/thread_token.c
additional_owners:
  - Sandboxie/core/drv/syscall.c
spec: docs/plan/srev-341-thread-change-notify-token-status-sentinel.md
schema: docs/plan/srev-341-thread-change-notify-token-status-sentinel.schema.json
checker: docs/plan/check-srev-341.py
runtime_gate: Windows non-zero-session GUI setup and NtSetInformationThread matrix for preserved change-notify impersonation normal token clear repeated committed calls and SREV-329 SREV-333 adjacency
---

### SREV-341: Thread Change Notify Token Status Sentinel

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | patched comment/topology after official `NtSetInformationThread`, impersonation-token, and privilege review; no behavior change |
| Evidence | `Thread_SetInformationThread_ChangeNotifyToken` intentionally returns `STATUS_THREAD_NOT_IN_PROCESS` after installing a restricted impersonation token for the current-thread change-notify path. `Syscall_Api_Invoke` consumes that status only when the syscall entry is `SetInformationThread` and `user_args[0] == NtCurrentThread()`, converts it to `STATUS_SUCCESS`, and skips `Thread_ClearThreadToken`. The old source called this a hack with a special status return code. |
| Data | `Thread_SetInformationThread_ImpersonationToken`, `Thread_SetInformationThread_ChangeNotifyToken`, `Syscall_Api_Invoke`, `Gui_ConnectToWindowStationAndDesktop`, `NtSetInformationThread`, `ThreadImpersonationToken`, `NtCurrentThread`, `InfoBuffer`, `MyTokenHandle`, `PsReferenceImpersonationToken`, `proc->primary_token`, `Token_Restrict`, `DISABLE_MAX_PRIVILEGE`, `Thread_MyImpersonateClient`, `SecurityImpersonation`, `proc->change_notify_token_flag`, `STATUS_THREAD_NOT_IN_PROCESS`, `STATUS_ALREADY_COMMITTED`, and `Thread_ClearThreadToken`. |
| Schema | `THREAD_CHANGE_NOTIFY_TOKEN_STATUS_SENTINEL` says `Thread_SetInformationThread_ChangeNotifyToken` owns the local `STATUS_THREAD_NOT_IN_PROCESS` producer for the current-thread change-notify-token path; `Syscall_Api_Invoke` owns the matching current-thread `SetInformationThread` sentinel consumer; the sentinel is a Sandboxie-private status signal and not a documented `NtSetInformationThread` result contract; the sentinel preserves impersonation across syscall return only for this request; normal primary-token syscall returns still clear temporary thread impersonation; SREV-329 and SREV-333 own adjacent `NtSetInformationThread` pass-through and Kaspersky/WOW64 sentinel topology; this SREV changes comments and proof only. |
| Topology | `Gui_ConnectToWindowStationAndDesktop -> NtSetInformationThread(CurrentThread, ThreadImpersonationToken, CurrentThread) -> Thread_SetInformationThread_ImpersonationToken -> Thread_SetInformationThread_ChangeNotifyToken -> PsReferenceImpersonationToken or primary-token fallback -> Token_Restrict(DISABLE_MAX_PRIVILEGE) -> Thread_MyImpersonateClient(SecurityImpersonation) -> STATUS_THREAD_NOT_IN_PROCESS -> Syscall_Api_Invoke current-thread SetInformationThread consumer -> STATUS_SUCCESS without Thread_ClearThreadToken`. |
| Logic Risk | The old hack wording hid a cross-owner status-sentinel contract. Future edits that broaden the consumer, clear the token unconditionally, or reuse `STATUS_THREAD_NOT_IN_PROCESS` for another path could break non-zero-session window-station/desktop setup or preserve impersonation for the wrong syscall. |
| Official Shape | Microsoft documents `Nt/ZwSetInformationThread` as a thread-information transition with thread handle, information class, information pointer, byte length, and NTSTATUS result. Microsoft documents `PsReferenceImpersonationToken` as returning a referenced thread impersonation token or `NULL`; `PsImpersonateClient` as assigning or ending thread impersonation and warning against raising untrusted user-thread privilege state; and `SE_CHANGE_NOTIFY_NAME` as the bypass traverse checking privilege. |
| Fix | Comment-only source clarification. `thread_token.c` now names SREV-341 and states that `STATUS_THREAD_NOT_IN_PROCESS` is a local current-thread change-notify-token sentinel used to return with impersonation still active. `syscall.c` now names the corresponding current-thread `SetInformationThread` consumer. No token selection, filtering, impersonation call, sentinel value, flag, status conversion, or token-clear behavior changed. |
| Acceptance Gate | `docs/plan/check-srev-341.py` validates the draft-07 schema, official references, `Thread_SetInformationThread_ImpersonationToken` trigger, `Thread_SetInformationThread_ChangeNotifyToken` token selection/filtering, `STATUS_THREAD_NOT_IN_PROCESS` producer, `Syscall_Api_Invoke` consumer, stale hack wording removal, SREV-329 / SREV-333 adjacency, combined ledger entry, and split ledger fragment; `docs/plan/check-srev-341.sh` is the targeted wrapper. Runtime gate: Windows VM matrix for non-zero-session process initialization and `Gui_ConnectToWindowStationAndDesktop`, proving the current-thread change-notify-token request returns success with impersonation intentionally preserved, normal `NtSetInformationThread` paths still clear temporary impersonation, repeated calls return the committed status, and browser/Kaspersky adjacent paths from SREV-329/SREV-333 do not regress. |
