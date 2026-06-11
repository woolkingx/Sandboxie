---
kind: srev-ledger-entry
id: SREV-168
title: Token Admin Membership Handle
status: patched-source-needs-windows-runtime
owner: Sandboxie/core/svc/sbieiniserver.h
spec: docs/plan/srev-168-token-admin-membership-handle.md
schema: docs/plan/srev-168-token-admin-membership-handle.schema.json
checker: docs/plan/check-srev-168.py
runtime_gate: "Windows SbieSvc build, PipeServer IsCallerAdmin non-admin limited-admin full-admin smoke, INI EditAdminOnly impersonation smoke, quick UAC token path smoke, and service-account membership isolation regression"
---

### SREV-168: Token Admin Membership Handle

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after Microsoft `CheckTokenMembership`, `TOKEN_TYPE`, `DuplicateToken`, and `TOKEN_ELEVATION_TYPE` documentation review; needs Windows service-token runtime proof |
| Evidence | `Sandboxie/core/svc/sbieiniserver.h` was the top unnamed reviewable core file after SREV-167. It declares `static bool TokenIsAdmin(HANDLE hToken, bool OnlyFull = false);`. Before this SREV, the implementation accepted `hToken` but called `CheckTokenMembership(NULL, AdministratorsGroup, &b)`, which makes Windows use the current thread effective token instead of the supplied token. `Sandboxie/core/svc/PipeServer.cpp` passes an explicit caller process token through `PipeServer::IsCallerAdmin`. |
| Data | `Sandboxie/core/svc/sbieiniserver.h`, `Sandboxie/core/svc/sbieiniserver.cpp`, `Sandboxie/core/svc/PipeServer.cpp`, `SbieIniServer::TokenIsAdmin`, `PipeServer::IsCallerAdmin`, `HANDLE hToken`, `CheckTokenMembership`, `GetTokenInformation`, `TOKEN_TYPE`, `TokenPrimary`, `TokenImpersonation`, `DuplicateToken`, `SecurityIdentification`, `TOKEN_DUPLICATE`, `TOKEN_QUERY`, and `TokenElevationType`. |
| Schema | `SBIEINI_TOKEN_ADMIN_MEMBERSHIP_HANDLE` says `sbieiniserver.h` owns the exported helper contract; `TokenIsAdmin` must evaluate the supplied `hToken`; primary tokens must be converted to impersonation tokens before `CheckTokenMembership`; duplicate tokens must be closed; `TokenElevationType` remains queried from the original token; and `PipeServer::IsCallerAdmin` must open caller process tokens with `TOKEN_QUERY | TOKEN_DUPLICATE`. |
| Topology | Legal flow is caller process/thread token -> broker obtains `hToken` -> `SbieIniServer::TokenIsAdmin(hToken, OnlyFull)` -> `GetTokenInformation(hToken, TokenType)` -> optional `DuplicateToken(hToken, SecurityIdentification)` for primary tokens -> `CheckTokenMembership(membershipToken, AdministratorsGroup)` -> `GetTokenInformation(hToken, TokenElevationType)` -> admin/full-admin decision for that supplied token. |
| Logic Risk | The old implementation mixed token owners: group membership came from the service thread's effective token while UAC elevation type came from `hToken`. That can produce decisions whose group membership and elevation state describe different tokens. Broker paths that already opened a caller token, such as `PipeServer::IsCallerAdmin`, must not accidentally ask whether the service thread is an administrator. |
| Official Shape | `docs/plan/srev-168-token-admin-membership-handle.md` records Microsoft `CheckTokenMembership`, `TOKEN_TYPE`, `DuplicateToken`, and `TOKEN_ELEVATION_TYPE` references. `docs/plan/srev-168-token-admin-membership-handle.schema.json` records the JSON Schema draft-07 local `SBIEINI_TOKEN_ADMIN_MEMBERSHIP_HANDLE` contract. |
| Fix | `TokenIsAdmin` now queries the supplied token's `TOKEN_TYPE`, checks impersonation tokens directly, converts primary tokens through `DuplicateToken(..., SecurityIdentification, ...)`, closes any duplicate membership token, and preserves the existing split-token elevation check on the original `hToken`. `PipeServer::IsCallerAdmin` now opens the caller process token with `TOKEN_QUERY | TOKEN_DUPLICATE` so primary-token conversion is legal. |
| Acceptance Gate | `docs/plan/check-srev-168.py` validates the draft-07 schema, official references, `sbieiniserver.h` owner surface, `TokenIsAdmin` supplied-token membership flow, primary-token duplication and close, stale `CheckTokenMembership(NULL, ...)` rejection, `PipeServer::IsCallerAdmin` token access rights, and ledger entry; `docs/plan/check-srev-168.sh` is the matrix wrapper. Runtime/build gate: Windows SbieSvc build; `PipeServer::IsCallerAdmin` smoke with non-admin, limited-admin, and full-admin caller process tokens; INI `EditAdminOnly` smoke while impersonating caller; quick UAC/elevate token path smoke; service-account membership isolation regression. |
