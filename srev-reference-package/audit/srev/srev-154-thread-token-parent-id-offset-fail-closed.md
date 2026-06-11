# SREV-154: Thread Token ParentId Offset Fail Closed

## Stage Gate

| Field | Content |
|---|---|
| Stage | schema -> boundary -> topology -> logic -> action -> verify |
| Input artifact | `Sandboxie/core/drv/thread.h`, `Sandboxie/core/drv/thread_token.c`, SREV-110 thread impersonation precedent, Microsoft token / impersonation / process-token references |
| Output artifact | Source-level hardening, draft-07 schema, checker, ledger fragment |
| Owner | `Sandboxie/core/drv/thread_token.c` owns primary-token assignment mediation for sandboxed process creation |
| Acceptance gate | Source proves public `TokenId` comes from `SeQueryInformationToken(TokenStatistics)` and private `ParentTokenId` offsets fail closed before any private token-object read |

## Data

`Thread_SetInformationProcess_PrimaryToken_3` mediates the token a sandboxed
parent may pass to a child process. The path obtains the current thread
impersonation token with `PsReferenceImpersonationToken`, then attempts to allow
that token when one of these local relation checks holds:

- `TokenObject2.ParentId == TokenObject1.TokenId`;
- `TokenObject2.ParentId == TokenObject1.ParentId`;
- either token has `SeAssignPrimaryTokenPrivilege`;
- a small compatibility exception applies.

Before this SREV, the function set `TokenId_offset` and
`ParentTokenId_offset` only for `Driver_OsVersion <= DRIVER_WINDOWS_10`. If the
offsets were not set, it logged `STATUS_UNKNOWN_REVISION` but still continued
to read `TokenObject + 0` in both `RtlEqualLuid` checks.

## Official Shape

Microsoft documents that `CreateProcessAsUser` may require
`SE_ASSIGNPRIMARYTOKEN_NAME` unless the token is an assignable or restricted
version of the caller's primary token. Restricted tokens are explicitly allowed
to create restricted processes without that privilege.

For kernel code, Microsoft documents `TOKEN_STATISTICS.TokenId` as a public
token identifier retrievable through `SeQueryInformationToken` or
`ZwQueryInformationToken`. Microsoft also documents that `SeQueryInformationToken`
allocates its returned buffer from paged pool and the caller must free it with
`ExFreePool`.

Microsoft does not expose a public `ParentTokenId` field for direct `PACCESS_TOKEN`
object-pointer arithmetic. That makes Sandboxie's `ParentTokenId_offset` a
private compatibility boundary, not an official API shape.

Official references:

- `https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-createprocessasusera`
- `https://learn.microsoft.com/en-us/windows/win32/secauthz/restricted-tokens`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/nf-ntifs-sequeryinformationtoken`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/ns-ntifs-_token_statistics`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/nf-ntifs-psimpersonateclient`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/ns-ntifs-_se_exports`

## Topology

Legal local topology:

```text
thread impersonation token
  -> Thread_SetInformationProcess_PrimaryToken_3
  -> public TokenObject1.TokenId via SeQueryInformationToken(TokenStatistics)
  -> private ParentTokenId offset only when the offset is known
  -> relation check or privilege/compatibility exception
  -> Token_AssignPrimaryHandle
```

Illegal topology:

```text
unknown OS/private token layout
  -> Log_Status(STATUS_UNKNOWN_REVISION)
  -> keep reading TokenObject + 0
  -> primary-token policy decision
```

## Logic Risk

The old unknown-revision branch did not actually fail closed. It logged the
unknown private layout, then continued with zero offsets. That can turn a
layout discovery failure into a policy decision over unrelated bytes at the
front of a token object.

The public API does not solve the full relation check because `ParentTokenId`
is not exposed as a documented token-information field. The correct local
contract is therefore mixed:

- use `TOKEN_STATISTICS.TokenId` for the public parent primary-token id;
- treat `ParentTokenId_offset` as private dynamic knowledge;
- deny the non-privileged relation path when the private offset is unknown;
- keep Windows runtime proof open because this is a kernel token path.

## Fix

`Thread_SetInformationProcess_PrimaryToken_3` now checks both
`TokenId_offset` and `ParentTokenId_offset` before any private token-object
field read. Unknown private layout logs `MSG_1222` / `0x63`, dereferences the
impersonation token, and returns `(void *)-1`.

The first relation check now obtains `TokenObject1.TokenId` through
`SeQueryInformationToken(TokenStatistics)` and frees the returned paged-pool
buffer with `ExFreePool`. The remaining `ParentTokenId` checks stay private and
are guarded by the known-offset gate.

## Acceptance Gate

`docs/plan/check-srev-154.py` validates the draft-07 schema, official
references, source hardening, stale offset-zero continuation removal, public
`TokenId` query, `ExFreePool` cleanup, and ledger fragment.

Runtime/build gate: Windows WDK build for `thread_token.c`; process creation
with a restricted token from a sandboxed parent; process creation with a
duplicated parent token; `SeAssignPrimaryTokenPrivilege` exception; compatibility
exceptions for `SandboxieDcomLaunch.exe` and `msiexec.exe`; synthetic or
instrumented unknown private-layout path proving `STATUS_PRIVILEGE_NOT_HELD`
instead of offset-zero reads; Driver Verifier and HVCI where supported.
