# SREV-252: Advapi Window Object Security Bypass

## Stage Gate

| Field | Value |
|---|---|
| Stage | schema -> topology -> logic -> action -> verify |
| Input artifact | `Sandboxie/core/dll/advapi.c`, SREV-116, SREV-126, Microsoft `SetSecurityInfo`, `GetSecurityInfo`, and `SE_OBJECT_TYPE` references |
| Output artifact | `docs/plan/srev-252-advapi-window-object-security-bypass.schema.json`, `docs/plan/check-srev-252.py`, `docs/plan/check-srev-252.sh`, ledger fragment, comment-only source clarification |
| Owner | `AdvApi_SetSecurityInfo` / `Ntmarta_SetSecurityInfo` Chrome window-object compatibility bypass |
| Acceptance gate | targeted source checker plus SREV-116 compatibility checker, core coverage, and diff checkpoint |

## Evidence

`advapi.c` has a paired Chrome 38 compatibility bypass in
`AdvApi_SetSecurityInfo` and `Ntmarta_SetSecurityInfo`:

```text
Chrome image
ObjectType == SE_WINDOW_OBJECT
handle == NULL
-> return ERROR_SUCCESS
```

The same file also has `GetSecurityInfo` fallback logic that retries DACL reads
on `Gui_Dummy_WinSta` for `SE_WINDOW_OBJECT`. SREV-116 owns the official
pointer-depth shape for `GetSecurityInfo`; SREV-126 owns the returned
`Gui_Dummy_WinSta` handle-ownership boundary. This SREV only clarifies the
Chrome null-handle `SetSecurityInfo` bypass comments.

Official references:

- https://learn.microsoft.com/en-us/windows/win32/api/aclapi/nf-aclapi-setsecurityinfo
- https://learn.microsoft.com/en-us/windows/win32/api/aclapi/nf-aclapi-getsecurityinfo
- https://learn.microsoft.com/en-us/windows/desktop/api/AccCtrl/ne-accctrl-se_object_type

## Data

`AdvApi_SetSecurityInfo`, `Ntmarta_SetSecurityInfo`, `Dll_ImageType`,
`DLL_IMAGE_GOOGLE_CHROME`, `SE_WINDOW_OBJECT`, null `handle`, `SecurityInfo`,
`DACL_SECURITY_INFORMATION`, `Gui_Dummy_WinSta`, and `ERROR_SUCCESS`.

## Schema

`ADVAPI_WINDOW_OBJECT_SECURITY_BYPASS` says:

- `SetSecurityInfo` sets security information for an object identified by a
  handle.
- `SE_WINDOW_OBJECT` is the object type for window stations and desktops.
- Sandboxie's Chrome compatibility bypass returns `ERROR_SUCCESS` only for
  Chrome `SE_WINDOW_OBJECT` calls with a null handle.
- `AdvApi_SetSecurityInfo` and `Ntmarta_SetSecurityInfo` must keep the same
  bypass predicate until Windows Chrome runtime proof supports narrowing it.
- `GetSecurityInfo` dummy-window-station DACL fallback remains owned by SREV-116
  and SREV-126 adjacency.
- This SREV does not change DACL mutation behavior, handle ownership, hook
  selection, ntmarta forwarding, or Chrome image detection.

## Topology

Advapi path:

```text
Chrome -> AdvApi_SetSecurityInfo
  -> SE_WINDOW_OBJECT + NULL handle
  -> report ERROR_SUCCESS without native call
```

Ntmarta path:

```text
Chrome -> Ntmarta_SetSecurityInfo
  -> SE_WINDOW_OBJECT + NULL handle
  -> report ERROR_SUCCESS without native call
```

Adjacent read path:

```text
GetSecurityInfo DACL read fails on window object
  -> Gui_Dummy_WinSta exists
  -> retry GetSecurityInfo on dummy window station
```

## Logic Risk

The old comments made the paired bypasses look like unexplained Chrome residue.
The real topology is a Chrome-specific null-handle window-object security
compatibility bypass, adjacent to the dummy window-station DACL read fallback.

It is tempting to narrow the bypass to `DACL_SECURITY_INFORMATION`, but the
comment does not prove Chrome 38's exact `SecurityInfo` mask. Narrowing the
predicate from Linux source review would be a behavior change without the
required Windows runtime matrix.

## Fix

Comment-only source clarification:

- `AdvApi_SetSecurityInfo` now names the Chrome null window-station/desktop
  security-handle probe.
- `Ntmarta_SetSecurityInfo` now says it owns the same Chrome null window-object
  security bypass.
- No condition, return value, native forwarding call, hook wiring, or
  `GetSecurityInfo` fallback changed.

## Acceptance Gate

`docs/plan/check-srev-252.py` validates the draft-07 schema, official reference
links, SREV-116/SREV-126 adjacency, paired bypass comments, unchanged bypass
predicates and forwarding calls, removal of stale Chrome 38 hack wording from
those sites, and the ledger fragment.

Runtime gate: Windows Chrome 38 or compatible Chrome sandbox launch matrix that
captures `SetSecurityInfo` / `Ntmarta_SetSecurityInfo` arguments for null
window-object calls before any predicate narrowing.
