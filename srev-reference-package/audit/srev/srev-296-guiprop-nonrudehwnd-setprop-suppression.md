# SREV-296: GuiProp NonRudeHWND SetProp Suppression

## Stage Gate

| Field | Value |
|---|---|
| Stage | schema -> boundary -> topology -> verify |
| Input artifact | `Sandboxie/core/dll/guiprop.c`, `Sandboxie/install/SbieSettings.ini`, `Sandboxie/core/drv/token.c`, `Sandboxie/core/svc/GuiServer.cpp`, Microsoft `SetPropW`, window properties, restricted token, and job UI restriction references |
| Output artifact | Source comment owner, draft-07 schema, targeted checker, ledger fragment |
| Owner | `Gui_InitProp` / `Gui_SetPropA` / `Gui_SetPropW` NonRudeHWND SetProp suppression |
| Acceptance gate | Targeted checker validates the source comment, SetProp suppression gates, token/UI-restriction owner separation, official references, stale comment removal, and ledger fragment |

## Data

`Gui_InitProp` initializes `Gui_NonRudeHWND_Hack` from `UseNonRudeHwndHack`,
defaulting to enabled outside app-compartment mode:

```text
Gui_NonRudeHWND_Hack =
  SbieApi_QueryConfBool(NULL, L"UseNonRudeHwndHack", !Dll_CompartmentMode)
```

`Gui_SetPropW` and `Gui_SetPropA` then report success without storing the
`NonRudeHWND` property when the flag is enabled and the property name is passed
as a string pointer. Other property writes continue through the existing
`Gui_HideWndProps`, accessibility, atom replacement, and `__sys_SetPropA/W`
paths.

The old source comment tied this narrow property suppression to
`UnrestrictedToken=y`. That option is a broader Sandboxie policy: settings
describe it as keeping the original security token and disabling token
restrictions; driver token code duplicates the original token for that setting;
`GuiServer.cpp` also uses `UnrestrictedToken` and `OriginalToken` to skip job UI
restrictions.

## Official Shape

Microsoft documents `SetPropW` as adding or changing an entry in a window
property list. The property name can be a string or a global atom, and success
means the string/data handle was added or changed.

Microsoft's window property overview defines a window property as data assigned
to a window, usually identified by a string name, and lists `GetProp`,
`SetProp`, `RemoveProp`, and enumeration functions as the property surface.

Microsoft documents restricted tokens as new access tokens derived from an
existing token with disabled SIDs, deleted privileges, and restricting SIDs.
That is a token-owner shape, not a window-property hook shape.

Microsoft documents `JOBOBJECT_BASIC_UI_RESTRICTIONS` as job-object UI
restriction state. Those restrictions include USER handle and clipboard related
limits and are configured through the job-object boundary, not through
`SetPropA/W`.

Official references:

- `https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setpropw`
- `https://learn.microsoft.com/en-us/windows/win32/winmsg/window-properties`
- `https://learn.microsoft.com/en-us/windows/win32/api/securitybaseapi/nf-securitybaseapi-createrestrictedtoken`
- `https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_basic_ui_restrictions`

## Schema

Local schema:

```text
docs/plan/srev-296-guiprop-nonrudehwnd-setprop-suppression.schema.json
```

Contract id:

```text
GUIPROP_NONRUDEHWND_SETPROP_SUPPRESSION
```

Primary contract:

```text
UseNonRudeHwndHack controls the NonRudeHWND SetPropA/W suppression
```

## Boundary

```text
UseNonRudeHwndHack setting
  -> Gui_NonRudeHWND_Hack
  -> Gui_SetPropA/W string-name check
  -> NonRudeHWND reports success without storage
  -> all other properties stay on existing SetProp paths
```

Separate boundary:

```text
UnrestrictedToken / OriginalToken policy
  -> driver token owner and GuiServer job UI restriction owner
  -> broad token/UI-restriction effect
```

## Topology

```text
SetPropA/W official shape
  -> window property list entry identified by string or atom
  -> Sandboxie guiprop hook may suppress one named property

UnrestrictedToken official-adjacent shape
  -> Sandboxie token policy
  -> Token_DuplicateToken / skip UIRestrictions
```

`guiprop.c` owns only the narrow window-property crossing. `token.c` and
`GuiServer.cpp` own the broader token and job UI restriction crossings.

## Logic Risk

The old comment made the narrow `NonRudeHWND` property rule sound like the
reason to enable `UnrestrictedToken=y`. That can route future maintenance or
user advice toward a broad token bypass when the local code already exposes a
more precise compatibility policy, `UseNonRudeHwndHack`.

## Fix

Comment-only source clarification. The source now names SREV-296, explains
that `UseNonRudeHwndHack` controls the `NonRudeHWND` SetProp suppression, and
states that `UnrestrictedToken` belongs to token/UI-restriction owners. No
setting default, string comparison, return value, atom replacement, access
check, or `__sys_SetPropA/W` call changed.

## Acceptance Gate

`docs/plan/check-srev-296.py` validates the draft-07 schema, official
references, source comment, unchanged `Gui_NonRudeHWND_Hack` default, unchanged
`NonRudeHWND` suppression checks in both ANSI and Unicode paths, stale comment
removal, token/UI-restriction owner evidence, combined ledger entry, and split
ledger fragment.

Runtime gate: Windows fullscreen behavior for apps that set `NonRudeHWND`
still needs targeted Windows runtime proof before changing policy defaults.

No setting default, string comparison, return value, atom replacement, access
check, or `__sys_SetPropA/W` path changed.
