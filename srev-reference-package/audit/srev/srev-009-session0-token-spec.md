# SREV-009 Session-0 CreateProcessAsUser Token Shape

Status: source-level spec before patch.

## Official Shape

`CreateProcessAsUserW` creates a new process in the security context of the user
represented by the specified token. The token handle is a primary token and must
have `TOKEN_QUERY`, `TOKEN_DUPLICATE`, and `TOKEN_ASSIGN_PRIMARY` access rights.
The process runs in the session specified in the token; `SetTokenInformation`
can change the session.

`DuplicateToken` creates an impersonation token and Microsoft explicitly states
that this token cannot be used with `CreateProcessAsUser`, which requires a
primary token. `DuplicateTokenEx(TokenPrimary)` is the API that can create a
primary token.

Sources:

- https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-createprocessasuserw
- https://learn.microsoft.com/en-us/windows/win32/api/securitybaseapi/nf-securitybaseapi-duplicatetoken
- https://learn.microsoft.com/en-us/windows/win32/api/securitybaseapi/nf-securitybaseapi-duplicatetokenex
- https://learn.microsoft.com/en-us/windows/win32/api/winnt/ne-winnt-token_type

## Local Shape

`RunSandboxedStartProcess` has a session-0 special path. The comment says it
starts the process using SbieSvc's own SYSTEM token when a reserved
`STARTUPINFOW::dwFlags` bit is set.

The same function also creates an impersonation token from the selected primary
token so file path/device-map probing can run under that token.

## Local Risk

The previous session-0 path opened SbieSvc's process token into
`PrimaryTokenHandle`, duplicated it into an impersonation token, then closed and
nulled `PrimaryTokenHandle` before calling `CreateProcessAsUser`.

That made the local code contradict its own session-0 comment and removed the
primary-token evidence before the API boundary that requires it.

## Patch Boundary

Keep the existing session-0 feature and the existing impersonation-token path.
Use a separate local handle owner for the temporary SbieSvc primary token:

- open SbieSvc's process token with the rights required by `CreateProcessAsUser`
- use it as the selected `PrimaryTokenHandle`
- duplicate it separately for thread impersonation
- keep it alive until after `CreateProcessAsUser`
- close only the local session-0 token handle before returning

## Acceptance Gate

- The session-0 path no longer closes/nuls the selected primary token before
  `CreateProcessAsUser`.
- `OpenProcessToken` failure is fail-closed and preserves `GetLastError`.
- The temporary session-0 primary token is closed before function return.
- Runtime gate remains open: a Windows session-0 launch smoke proves the child
  process token/session matches the intended SbieSvc SYSTEM token path.
