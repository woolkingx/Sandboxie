# SREV-251: Advapi Change Notify Privilege Filter

## Stage Gate

| Field | Value |
|---|---|
| Stage | schema -> topology -> logic -> action -> verify |
| Input artifact | `Sandboxie/core/dll/advapi.c`, Microsoft `CreateRestrictedToken`, `LookupPrivilegeValueW`, and privilege-constant references |
| Output artifact | `docs/plan/srev-251-advapi-change-notify-privilege-filter.schema.json`, `docs/plan/check-srev-251.py`, `docs/plan/check-srev-251.sh`, ledger fragment, source-level privilege filter hardening |
| Owner | `AdvApi_CreateRestrictedToken` Chrome dropped-rights compatibility filter |
| Acceptance gate | targeted source checker plus core coverage/diff checkpoint; Windows Chrome dropped-rights runtime proof remains required |

## Evidence

`AdvApi_CreateRestrictedToken` hooks `CreateRestrictedToken` and filters
`SE_CHANGE_NOTIFY_NAME` out of the caller's `PrivilegesToDelete` array so
Chrome's dropped-rights token keeps traverse-checking bypass semantics.

Before this SREV, the source admitted the path as:

```text
This is a HACK to get Chrome 37 to work with dropped rights. A work in progress.
```

The code also ignored the `LookupPrivilegeValueW` result, allocated a scratch
`LUID_AND_ATTRIBUTES` array without checking allocation success, and used a
nested loop that reused the same `i` variable for both loop levels.

Official references:

- https://learn.microsoft.com/en-us/windows/win32/api/securitybaseapi/nf-securitybaseapi-createrestrictedtoken
- https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-lookupprivilegevaluew
- https://learn.microsoft.com/en-us/windows/win32/secauthz/privilege-constants

## Data

`ExistingTokenHandle`, `Flags`, `DeletePrivilegeCount`, `PrivilegesToDelete`,
`LUID_AND_ATTRIBUTES`, `LookupPrivilegeValueW`, `SE_CHANGE_NOTIFY_NAME`,
`SeChangeNotifyPrivilege`, `pModifiedPrivilegesToDelete`,
`CreateRestrictedToken`, and `NewTokenHandle`.

## Schema

`ADVAPI_CHANGE_NOTIFY_PRIVILEGE_FILTER` says:

- `CreateRestrictedToken` receives a count plus optional array of privileges to
  delete from the new restricted token.
- `LookupPrivilegeValueW` resolves `SE_CHANGE_NOTIFY_NAME` to the local LUID
  used for comparison.
- `SE_CHANGE_NOTIFY_NAME` is the traverse-checking bypass privilege and is
  enabled by default for all users.
- Sandboxie's Chrome compatibility filter may remove only that LUID from the
  delete list.
- If lookup or scratch allocation fails, the hook must call the real
  `CreateRestrictedToken` with the original privilege-delete arguments.
- This SREV does not change SID disabling, restricted SID handling, token type,
  returned handle ownership, or Chrome image detection.

## Topology

```text
Chrome process
  -> AdvApi_CreateRestrictedToken hook
  -> resolve SE_CHANGE_NOTIFY_NAME to LUID
  -> build scratch delete-list without that one LUID
  -> __sys_CreateRestrictedToken
  -> NewTokenHandle returned by Windows
```

Failure/fallback path:

```text
lookup fails OR scratch allocation fails OR delete list lacks SeChangeNotify
  -> original DeletePrivilegeCount / PrivilegesToDelete pass through unchanged
```

## Logic Risk

The old comment hid a precise token-privilege compatibility rule. The old code
also relied on lookup and allocation success without checking either and reused
the same loop variable in a nested loop. If allocation failed with a nonzero
delete count, the hook could pass a modified count with a null modified array
instead of the original Windows arguments.

The legal fix is narrow: keep the Chrome compatibility behavior, but make the
filter an explicit optional transform that only takes effect when the local LUID
is resolved and the scratch list exists.

## Fix

`AdvApi_CreateRestrictedToken` now:

- names the rule as preserving Chrome dropped-rights traverse-checking bypass;
- checks `DeletePrivilegeCount`, `PrivilegesToDelete`, and
  `LookupPrivilegeValueW` before filtering;
- checks the `GlobalAlloc` result before writing the scratch list;
- uses one loop over the delete list;
- switches to the modified list only if `SE_CHANGE_NOTIFY_NAME` was found;
- otherwise passes the original privilege-delete arguments to
  `__sys_CreateRestrictedToken`.

## Acceptance Gate

`docs/plan/check-srev-251.py` validates the draft-07 schema, official
reference links, new filter/fallback topology, removal of the stale Chrome 37
hack wording, single-loop source shape, unchanged SID arguments and returned
token handle path, and the ledger fragment.

Runtime/build gate: Windows build for `advapi.c`; Chrome dropped-rights launch
smoke proving `SeChangeNotifyPrivilege` remains available when Chrome requests
its deletion; negative smoke where the delete list lacks the privilege and the
original list is forwarded unchanged; allocation-failure path is source-gated
only unless fault injection is available.
