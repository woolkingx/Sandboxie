---
kind: srev-ledger-entry
id: SREV-154
title: Thread Token ParentId Offset Fail Closed
status: patched-source-level-after-official-token-statistics-and-primary-token-review-needs-windows-runtime-proof
owner: Sandboxie/core/drv/thread_token.c
spec: docs/plan/srev-154-thread-token-parent-id-offset-fail-closed.md
schema: docs/plan/srev-154-thread-token-parent-id-offset-fail-closed.schema.json
checker: docs/plan/check-srev-154.py
runtime_gate: Windows primary-token assignment and private token-layout runtime proof
---

### SREV-154: Thread Token ParentId Offset Fail Closed

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official token statistics / restricted-token / primary-token privilege review; needs Windows primary-token assignment runtime proof |
| Evidence | `Sandboxie/core/drv/thread.h` is the top unnamed reviewable core file after SREV-153, and its token state is consumed by `Sandboxie/core/drv/thread_token.c`. `Thread_SetInformationProcess_PrimaryToken_3` mediates the token a sandboxed parent may pass to a child process. Before this SREV, `TokenId_offset` and `ParentTokenId_offset` were set only for `Driver_OsVersion <= DRIVER_WINDOWS_10`; when the private offsets were unknown, the code logged `STATUS_UNKNOWN_REVISION` but still continued into `RtlEqualLuid` with zero offsets. |
| Data | `Thread_SetInformationProcess_PrimaryToken_3`, `Thread_SetInformationProcess_PrimaryToken_2`, `THREAD::token_object`, `token_CopyOnOpen`, `token_EffectiveOnly`, `token_ImpersonationLevel`, `PsReferenceImpersonationToken`, `TokenId_offset`, `ParentTokenId_offset`, `TOKEN_STATISTICS.TokenId`, `SeQueryInformationToken`, `ExFreePool`, `RtlEqualLuid`, `Token_CheckPrivilege`, `SE_ASSIGNPRIMARYTOKEN_PRIVILEGE`, `STATUS_UNKNOWN_REVISION`, and `STATUS_PRIVILEGE_NOT_HELD`. |
| Schema | `THREAD_TOKEN_PARENT_ID_OFFSET_FAIL_CLOSED` says `TOKEN_STATISTICS.TokenId` is the documented public token id source for `TokenObject1`, `SeQueryInformationToken` returns a paged-pool buffer that must be freed with `ExFreePool`, `ParentTokenId` is not exposed as a documented `PACCESS_TOKEN` field, `ParentTokenId_offset` is private compatibility data, and unknown token private layout must log `STATUS_UNKNOWN_REVISION`, dereference `TokenObject2`, and return `(void *)-1` before relation checks. |
| Topology | Legal flow is thread impersonation token -> `Thread_SetInformationProcess_PrimaryToken_3` -> public `TokenObject1.TokenId` through `SeQueryInformationToken(TokenStatistics)` -> private `ParentTokenId` only when known -> relation check or privilege/compatibility exception -> `Token_AssignPrimaryHandle`. |
| Logic Risk | The old unknown-revision path did not fail closed. It converted a private token-layout discovery failure into LUID comparison over offset zero, so a non-privileged token relation decision could be made from unrelated token-object bytes. |
| Official Shape | `docs/plan/srev-154-thread-token-parent-id-offset-fail-closed.md` records Microsoft `CreateProcessAsUser`, restricted token, `SeQueryInformationToken`, `TOKEN_STATISTICS`, `PsImpersonateClient`, and `SE_EXPORTS` references. `docs/plan/srev-154-thread-token-parent-id-offset-fail-closed.schema.json` records the JSON Schema draft-07 local `THREAD_TOKEN_PARENT_ID_OFFSET_FAIL_CLOSED` contract. |
| Fix | `thread_token.c` now checks both `TokenId_offset` and `ParentTokenId_offset` before any private token-object field read. Unknown private layout logs `MSG_1222` / `0x63`, dereferences the referenced impersonation token, and returns `(void *)-1`. The first relation check now obtains `TokenObject1.TokenId` through `SeQueryInformationToken(TokenStatistics)` and frees the returned buffer with `ExFreePool`; the remaining private `ParentTokenId` relation stays guarded by the known-offset gate. |
| Acceptance Gate | `docs/plan/check-srev-154.py` validates the draft-07 schema, official references, source hardening, stale offset-zero continuation removal, public `TokenId` query, `ExFreePool` cleanup, preservation of privilege/compatibility exceptions, and ledger fragment; `docs/plan/check-srev-154.sh` is the matrix wrapper. Runtime/build gate: Windows WDK build for `thread_token.c`; restricted-token child process creation; duplicated-parent-token child process creation; `SeAssignPrimaryTokenPrivilege` exception; `SandboxieDcomLaunch.exe` / `msiexec.exe` compatibility exceptions; unknown private-layout fail-closed proof; Driver Verifier and HVCI where supported. |
