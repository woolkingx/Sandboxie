# SREV-168: Token Admin Membership Handle

## Stage Gate

```text
stage: schema -> boundary -> topology -> logic -> action -> verify
input artifact: Sandboxie/core/svc/sbieiniserver.h, sbieiniserver.cpp, PipeServer.cpp, and Microsoft token membership documentation
output artifact: TokenIsAdmin evaluates the supplied token handle instead of the service thread token
owner: Sandboxie/core/svc/sbieiniserver.h
acceptance gate: docs/plan/check-srev-168.py and docs/plan/check-srev-168.sh
```

## Data

`sbieiniserver.h` exposes:

```cpp
static bool TokenIsAdmin(HANDLE hToken, bool OnlyFull = false);
```

The implementation is used both while `SbieIniServer` is impersonating a
caller and by other service brokers that pass explicit caller tokens, including
`PipeServer::IsCallerAdmin`, quick UAC token handling, and process launch token
selection.

Before this SREV, `TokenIsAdmin` accepted `hToken` but called:

```cpp
CheckTokenMembership(NULL, AdministratorsGroup, &b)
```

That makes the membership question depend on the current service thread's
effective token, not necessarily the token supplied by the caller.

## Official Shape

- Microsoft documents `CheckTokenMembership` as checking whether a SID is
  enabled in an access token. Its `TokenHandle` parameter must be a
  `TOKEN_QUERY` impersonation token. When `TokenHandle` is `NULL`, Windows uses
  the calling thread's impersonation token, or duplicates the thread's primary
  token if the thread is not impersonating:
  `https://learn.microsoft.com/en-us/windows/win32/api/securitybaseapi/nf-securitybaseapi-checktokenmembership`.
- Microsoft documents `TOKEN_TYPE` as the distinction between primary and
  impersonation tokens:
  `https://learn.microsoft.com/en-us/windows/win32/api/winnt/ne-winnt-token_type`.
- Microsoft documents `DuplicateToken` as creating an impersonation token from
  an existing token opened with `TOKEN_DUPLICATE`, and says the duplicate handle
  has `TOKEN_IMPERSONATE` and `TOKEN_QUERY`:
  `https://learn.microsoft.com/en-us/windows/win32/api/securitybaseapi/nf-securitybaseapi-duplicatetoken`.
- Microsoft documents `TOKEN_ELEVATION_TYPE` values as default, full, and
  limited elevation states queried through `GetTokenInformation`:
  `https://learn.microsoft.com/en-us/windows/win32/api/winnt/ne-winnt-token_elevation_type`.

## Schema

`SBIEINI_TOKEN_ADMIN_MEMBERSHIP_HANDLE` says:

- `sbieiniserver.h` owns the exported service helper contract for
  `TokenIsAdmin`.
- `TokenIsAdmin` must evaluate the supplied `hToken`, not a hidden service
  thread token.
- If `hToken` is primary, it must be converted to an impersonation token before
  `CheckTokenMembership`.
- Any duplicate token created for membership checking must be closed.
- UAC split-token handling still queries `TokenElevationType` from the original
  supplied token.
- `PipeServer::IsCallerAdmin` must open caller process tokens with both
  `TOKEN_QUERY` and `TOKEN_DUPLICATE`, because it may pass a primary token to
  `TokenIsAdmin`.
- Linux source gates are not Windows service-token runtime proof.

## Topology

Legal flow:

```text
caller process/thread token
  -> service broker obtains hToken
  -> SbieIniServer::TokenIsAdmin(hToken, OnlyFull)
  -> GetTokenInformation(hToken, TokenType)
  -> if primary: DuplicateToken(hToken, SecurityIdentification)
  -> CheckTokenMembership(membershipToken, AdministratorsGroup)
  -> GetTokenInformation(hToken, TokenElevationType)
  -> return admin/full-admin decision for that supplied token
```

`CheckTokenMembership(NULL, ...)` is legal only when the desired subject is the
current thread's effective token. This helper's subject is the explicit
`hToken`.

## Logic Risk

The old implementation mixed two owners: group membership came from the
service thread's effective token, while UAC elevation type came from `hToken`.
That can produce decisions whose group membership and elevation state describe
different tokens. In broker paths such as `PipeServer::IsCallerAdmin`, the
service already opens the caller process token, so using the current service
thread token is the wrong boundary.

## Fix

`TokenIsAdmin` now queries `TokenType` for `hToken`. Impersonation tokens are
checked directly. Primary tokens are duplicated to an impersonation token with
`DuplicateToken(..., SecurityIdentification, ...)` and the duplicate is closed
after `CheckTokenMembership`. The existing split-token elevation logic remains
based on the original `hToken`.

`PipeServer::IsCallerAdmin` now opens the caller process token with
`TOKEN_QUERY | TOKEN_DUPLICATE` so a primary process token can be converted by
`TokenIsAdmin`.

## Verification

Source-level gates:

```bash
python3 docs/plan/check-srev-168.py
bash docs/plan/check-srev-168.sh
python3 docs/plan/check-core-coverage.py
```

Full closure matrix:

```bash
python3 docs/plan/check-srev-168.py &&
bash docs/plan/check-srev-168.sh &&
python3 docs/plan/check-core-coverage.py &&
for s in docs/plan/check-srev-0*.sh docs/plan/check-srev-1*.sh docs/plan/check-kpath-0*.sh; do bash "$s"; done &&
git diff --check
```

Runtime/build gate: Windows SbieSvc build; `PipeServer::IsCallerAdmin` smoke
with non-admin, limited-admin, and full-admin caller process tokens; INI
`EditAdminOnly` smoke while impersonating caller; quick UAC/elevate token path
smoke; regression that service account membership does not decide caller token
membership.
