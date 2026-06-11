# SREV-316: Ntmarta Window Security Hook Selection

## Stage Gate

| Field | Value |
|---|---|
| Stage | data -> schema -> topology -> logic -> action -> verify |
| Input artifact | `Sandboxie/core/dll/advapi.c`, `Sandboxie/core/dll/ldr.c`, `Sandboxie/core/dll/guienum.c`, Microsoft `GetSecurityInfo`, `SetSecurityInfo`, `SE_OBJECT_TYPE`, window-station/desktop security, and `CreateDesktopW` documentation |
| Output artifact | ntmarta window-object security hook-selection contract, draft-07 schema, targeted checker, ledger fragment |
| Owner | `Ntmarta_Init` in `Sandboxie/core/dll/advapi.c` |
| Acceptance gate | Targeted checker validates official references, loader registration, hook-selection predicates, Advapi32/ntmarta recursion boundary, SREV-116/SREV-126/SREV-252 adjacency, CreateDesktopW NULL-security fallback adjacency, combined ledger, and ledger fragment |

## Data

`ldr.c` registers `ntmarta.dll` with `Ntmarta_Init`. `Ntmarta_Init` resolves
`GetSecurityInfo` from `ntmarta.dll`, publishes it through `__sys_GetSecurityInfo`
when the sandbox desktop hack path is enabled, and installs the ntmarta
`GetSecurityInfo` hook only for 32-bit Acrobat Reader. On 64-bit Chrome it also
resolves `SetSecurityInfo` from `ntmarta.dll` and publishes it as
`__sys_SetSecurityInfo` when Advapi32 did not provide the API path.

`Ntmarta_GetSecurityInfo` first calls the native ntmarta API. If that fails for
`SE_WINDOW_OBJECT` DACL security and `Gui_Dummy_WinSta` exists, it retries
against the dummy window station. That fallback is owned by SREV-116 and
SREV-126.

`Ntmarta_SetSecurityInfo` owns the Chrome null window-object security bypass
mirrored from `AdvApi_SetSecurityInfo`. That compatibility branch is owned by
SREV-252.

`Gui_CreateDesktopW` first tries the caller-supplied security attributes, then
switches through `Gui_Dummy_WinSta`, and finally can retry with NULL security
attributes for the desktop-hack process set. This SREV records that adjacency
because the source comment ties that path to ntmarta `GetSecurityInfo`; it does
not change the `Gui_CreateDesktopW` behavior.

## Official Shape

Microsoft documents `GetSecurityInfo` as retrieving a security descriptor for
an object identified by handle and `SE_OBJECT_TYPE`. The returned owner, group,
DACL, and SACL pointers are valid through the returned security descriptor, and
the caller must free the returned descriptor with `LocalFree`.

Microsoft documents `SetSecurityInfo` as setting security information for an
object identified by handle and `SE_OBJECT_TYPE`. A NULL DACL with
`DACL_SECURITY_INFORMATION` grants full access to everyone, so Sandboxie must
keep Chrome's null-handle `SE_WINDOW_OBJECT` bypass scoped to the known
compatibility predicate instead of treating NULL DACL/security input broadly.

Microsoft documents `SE_WINDOW_OBJECT` as a local window-station or desktop
object. SREV-316 treats `SE_WINDOW_OBJECT` as a local window-station or desktop
object, not as a named global object. `GetNamedSecurityInfo` and
`SetNamedSecurityInfo` are not valid for these objects because the names are not
unique.

Source gate phrase: SE_WINDOW_OBJECT as a local window-station or desktop object.
Source gate phrase: CreateDesktopW with NULL security attributes.

Microsoft documents window stations and desktops as securable objects. Window
stations contain one or more desktops; desktops contain windows, menus, and
hooks. The security descriptor for a window station or desktop is queried and
set through `GetSecurityInfo` and `SetSecurityInfo`.

Microsoft documents `CreateDesktopW` as creating a desktop associated with the
current window station of the calling process. If its security-attributes
parameter is NULL, the desktop inherits its security descriptor from the parent
window station.

Official references:

- `https://learn.microsoft.com/en-us/windows/win32/api/aclapi/nf-aclapi-getsecurityinfo`
- `https://learn.microsoft.com/en-us/windows/win32/api/aclapi/nf-aclapi-setsecurityinfo`
- `https://learn.microsoft.com/en-us/windows/win32/api/accctrl/ne-accctrl-se_object_type`
- `https://learn.microsoft.com/en-us/windows/win32/winstation/about-window-stations-and-desktops`
- `https://learn.microsoft.com/en-us/windows/win32/winstation/window-station-security-and-access-rights`
- `https://learn.microsoft.com/en-us/windows/win32/winstation/desktop-security-and-access-rights`
- `https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-createdesktopw`

## Schema

Local schema:

```text
docs/plan/srev-316-ntmarta-window-security-hook-selection.schema.json
```

Contract id:

```text
NTMARTA_WINDOW_SECURITY_HOOK_SELECTION
```

## Topology

```text
ntmarta.dll load
  -> Ldr_Dlls entry
  -> Ntmarta_Init
  -> Ldr_GetProcAddrNew("GetSecurityInfo")
  -> desktop-hack image/config predicate and !OpenWndStation
  -> publish __sys_GetSecurityInfo
  -> 32-bit Acrobat Reader only: install Ntmarta_GetSecurityInfo hook
  -> Ntmarta_GetSecurityInfo
  -> native ntmarta GetSecurityInfo
  -> failed SE_WINDOW_OBJECT DACL + Gui_Dummy_WinSta
  -> retry against dummy window station
```

```text
64-bit Chrome
  -> Ntmarta_Init
  -> Ldr_GetProcAddrNew("SetSecurityInfo")
  -> publish __sys_SetSecurityInfo only as Advapi32-missing fallback
  -> Ntmarta_SetSecurityInfo
  -> SREV-252 Chrome null SE_WINDOW_OBJECT bypass
  -> native ntmarta SetSecurityInfo otherwise
```

Boundary:

```text
caller desktop/security setup
  -> Advapi32 or ntmarta security API front door
  -> SE_WINDOW_OBJECT handle semantics
  -> real or dummy window-station owner
```

Sandboxie owns only hook selection and compatibility fallback routing here. It
does not own the Windows security descriptor schema, named-object uniqueness, or
the final runtime truth of whether Chrome/Acrobat still need the legacy
predicate.

## Logic Risk

The old loader comment called the entry a generic Chrome/Acrobat workaround and
the owner comments described recursion and stack-overflow risk without naming
the legal API boundary. That makes later edits likely to widen hooks or change
predicates without realizing that three adjacent SREVs own different behavior:

- SREV-116: `GetSecurityInfo` signature/out-parameter shape and dummy
  window-station DACL fallback.
- SREV-126: `Gui_Dummy_WinSta` handle ownership and duplicate-handle boundary.
- SREV-252: Chrome null `SE_WINDOW_OBJECT` `SetSecurityInfo` bypass.

## Fix

`ldr.c` now names the `ntmarta.dll` entry as the SREV-316 window-object
security hook-selection path. `Ntmarta_Init` comments now identify the
SREV-116/SREV-126 dummy-window-station fallback, the SREV-252 Chrome
`SetSecurityInfo` fallback, and the Advapi32/ntmarta delay-loading recursion
boundary.

No hook predicate, image condition, `OpenWndStation` condition, export lookup,
function-pointer assignment, native call, retry condition, or return value
changed.

## Acceptance Gate

`docs/plan/check-srev-316.py` validates the draft-07 schema, official
references, loader table registration, `GetSecurityInfo` and `SetSecurityInfo`
resolution, hook/publication predicates, no broad ntmarta hook installation,
source comments, SREV adjacency, `Gui_CreateDesktopW` NULL-security retry
adjacency, combined ledger entry, and split ledger fragment.

Runtime gate: Windows Chrome/Acrobat desktop creation and window-station
security smoke with call capture for Advapi32 and ntmarta `GetSecurityInfo` /
`SetSecurityInfo`, proving no recursion, no widened process/image predicate,
and no regression in the SREV-116/SREV-126/SREV-252 adjacent paths.
