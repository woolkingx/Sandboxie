---
kind: srev-ledger-entry
id: SREV-300
title: IPC Self Impersonation Status Gate
status: patched-source-level-self-impersonation-status-gate-needs-windows-runtime-proof
owner: Sandboxie/core/dll/ipc.c
spec: docs/plan/srev-300-ipc-self-impersonation-status-gate.md
schema: docs/plan/srev-300-ipc-self-impersonation-status-gate.schema.json
checker: docs/plan/check-srev-300.py
runtime_gate: Windows LPC/ALPC impersonation smoke with native success, self-token fallback success, forced duplicate/install failure, and RPCSS/admin exception behavior
---

### SREV-300: IPC Self Impersonation Status Gate

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level self-impersonation status gate; needs Windows runtime proof |
| Evidence | `Ipc_NtImpersonateClientOfPort` and `Ipc_NtAlpcImpersonateClientOfPort` call native client impersonation first, then route non-system callers through `Ipc_ImpersonateSelf`. `Ipc_ImpersonateSelf` checks whether the current thread token is already at `SecurityImpersonation`; otherwise it clears active impersonation, opens this process token with `TOKEN_DUPLICATE`, duplicates it as `TokenImpersonation` with `TOKEN_IMPERSONATE | TOKEN_QUERY`, and installs it through `ThreadImpersonationToken`. Before this patch, failure in the self-token path still returned `STATUS_SUCCESS`. |
| Data | `Ipc_ImpersonateSelf`, `Ipc_NtImpersonateClientOfPort`, `Ipc_NtAlpcImpersonateClientOfPort`, `NtOpenThreadToken`, `NtQueryInformationToken(TokenImpersonationLevel)`, `SecurityImpersonation`, `SecurityIdentification`, `NtSetInformationThread(ThreadImpersonationToken)`, `NtOpenProcessToken(TOKEN_DUPLICATE)`, `NtDuplicateToken(TokenImpersonation)`, `TOKEN_IMPERSONATE`, `TOKEN_QUERY`, `hOldToken`, `hNewToken`, `hPriToken`, `Dll_IsSystemSid`, and SREV-110. |
| Schema | `IPC_SELF_IMPERSONATION_STATUS_GATE` says `Ipc_ImpersonateSelf` success means an existing `SecurityImpersonation` token was preserved or a self `TokenImpersonation` token was installed; `NtQueryInformationToken(TokenImpersonationLevel)` owns the current thread token level read; `NtDuplicateToken(TokenImpersonation)` owns the self primary-token to impersonation-token conversion; `NtSetInformationThread(ThreadImpersonationToken)` owns the thread-token install result; `Ipc_ImpersonateSelf` must return the actual self-impersonation status; SREV-110 owns the adjacent driver-side private-offset impersonation replay shim. |
| Topology | `Native LPC/ALPC impersonation result -> Ipc_ImpersonateSelf -> active SecurityImpersonation token or duplicated self token -> wrapper NTSTATUS result`; failure path: `self-token duplicate/install failure -> restore old thread token when present -> return failure status`. |
| Logic Risk | The old code conflated caller compatibility with proof that a legal impersonation state existed. Returning `STATUS_SUCCESS` after `NtOpenProcessToken`, `NtDuplicateToken`, or `NtSetInformationThread` failed could let later work run without a usable `SecurityImpersonation` token, the same class of problem the comment described as later `STATUS_BAD_IMPERSONATION_LEVEL`. |
| Official Shape | Microsoft documents `NtQueryInformationToken(TokenImpersonationLevel)`, `NtDuplicateToken(TokenImpersonation)`, `SECURITY_IMPERSONATION_LEVEL`, `NtSetInformationThread`, and `PsImpersonateClient` as the relevant token/impersonation shapes. Public Microsoft documentation does not define this exact `NtAlpcImpersonateClientOfPort` wrapper shape, so the ALPC wrapper is treated as local source evidence while the token operations are checked against documented token APIs. |
| Fix | `Ipc_ImpersonateSelf` now returns the actual status from the self-impersonation path. Existing fast-path success for already-usable impersonation tokens is unchanged. On failure, the function still attempts to restore the old thread token before returning the failure status. The ALPC source comment now names SREV-300 and says success means the self path actually installed or preserved a `SecurityImpersonation` token. No token access mask, impersonation level, RPCSS/admin exception, native call, or system-SID bypass changed. |
| Acceptance Gate | `docs/plan/check-srev-300.py` validates the draft-07 schema, official references, source status return, unchanged token query/duplicate/install shape, restore-on-error path, system-SID bypass preservation, SREV-110 adjacency, stale wording removal, combined ledger entry, and split ledger fragment; `docs/plan/check-srev-300.sh` is the targeted wrapper. Runtime gate: Windows LPC/ALPC impersonation smoke covering successful native client impersonation, identification-level native result followed by successful self-token install, forced `NtDuplicateToken`/`NtSetInformationThread` failure returning a failure status, and RPCSS/admin exception behavior. |
