# SREV-334: GUI Clipboard Integrity Bridge

| Field | Content |
|---|---|
| Stage | schema -> topology -> verify |
| Input artifact | `Sandboxie/core/drv/gui.c`, `Sandboxie/core/svc/GuiServer.cpp`, `Sandboxie/core/dll/gui.c`, Microsoft clipboard, window station, Mandatory Integrity Control, and UIPI documentation |
| Output artifact | Source comment owner, draft-07 schema, checker, and ledger fragment |
| Owner | `Gui_Api_Clipboard` private clipboard item integrity bridge |
| Acceptance gate | Targeted checker validates official references, service-only caller gate, clipboard lock/open topology, dynamic item-layout probe, integrity rewrite gate, stale bug/workaround wording removal, and ledger fragment |

## Data

`gui.c` contains the driver side of `API_GUI_CLIPBOARD`. The path:

- references the current process window station;
- uses `Dyndata_Config.Clipboard_offset` to reach the private clipboard area;
- learns the clipboard item entry length and integrity-index slot by observing
  sentinel clipboard formats `0x111111`, `0x222222`, `0x333333`, and `0x444444`;
- rewrites item integrity labels only when they match known MIC values;
- rejects non-service callers because the driver does not own clipboard locking;
- is invoked by `GuiServer::CloseClipboardSlave` while SbieSvc has opened the
  clipboard and forces delayed rendering with `EnumClipboardFormats` /
  `GetClipboardData`.

The old comment framed this as a Windows bug workaround. The more useful
contract is a three-layer bridge:

```text
public clipboard ownership/open/close protocol
  -> window-station clipboard storage
  -> private win32k clipboard item integrity slot
```

## Official Shape

Microsoft documents the clipboard as a data-transfer facility where all
applications have access, with the security warning that it should not be used
for sensitive data. Clipboard operations require `OpenClipboard`; only one
window can have the clipboard open at a time; callers close it with
`CloseClipboard`. `SetClipboardData` can use delayed rendering by passing
`NULL` as the data handle.

Microsoft documents a window station as containing a clipboard, atom table, and
desktops. `WINSTA_ACCESSCLIPBOARD` is required to use the clipboard.

Microsoft documents Mandatory Integrity Control as assigning integrity levels
to principals and securable objects. Lower-integrity principals are restricted
from writing up by default. Microsoft documents UIPI as blocking UI messages
from lower-integrity senders to higher-integrity windows unless a message filter
allows it.

Official references:

- `https://learn.microsoft.com/en-us/windows/win32/dataxchg/clipboard`
- `https://learn.microsoft.com/en-us/windows/win32/dataxchg/clipboard-operations`
- `https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setclipboarddata`
- `https://learn.microsoft.com/en-us/windows/win32/winstation/window-stations`
- `https://learn.microsoft.com/en-us/windows/win32/winstation/window-station-security-and-access-rights`
- `https://learn.microsoft.com/en-us/windows/win32/secauthz/mandatory-integrity-control`
- `https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-changewindowmessagefilterex`

## Boundary

```text
Gui_CloseClipboard in sandboxed DLL
  -> SbieSvc CloseClipboardSlave
  -> OpenClipboard / delayed-rendering drain
  -> API_GUI_CLIPBOARD service-only driver call
  -> current window-station clipboard private item area
  -> integrity label rewrite
```

The public clipboard API owns open/close, ownership, delayed rendering, and
format enumeration. The window-station object owns the documented clipboard
container. Sandboxie's driver owns only the private observed item-layout probe
and integrity-slot rewrite after SbieSvc has made the clipboard stable enough
for that probe.

## Topology

```text
Gui_Api_Clipboard
  -> Vista+ gate
  -> proc == NULL and MyIsCallerMyServiceProcess()
  -> init: parms[1] == -1 -> Gui_InitClipboard
  -> fix: item length/index known -> Gui_FixClipboard(integrity)

Gui_InitClipboard
  -> Gui_ReferenceClipboard
  -> Dyndata_Config.Clipboard_offset
  -> sentinel formats 0x111111..0x444444
  -> derive item length and integrity index

Gui_FixClipboard
  -> known MIC labels 0x0000..0x4000
  -> rewrite item integrity slot

CloseClipboardSlave
  -> OpenClipboard
  -> SbieApi_Call(API_GUI_CLIPBOARD, 0x4000)
  -> EnumClipboardFormats / GetClipboardData
  -> CloseClipboard
```

## Logic Risk

The stale comment made a private win32k observation look like the API contract.
Future work could hard-code a new layout, call the API without the service-held
clipboard lock, or widen the caller gate. The correct owner split is stricter:
official clipboard/window-station APIs define the public protocol, while
Sandboxie's dynamic probe owns only the private clipboard item layout for the
running Windows build.

## Fix

Comment-only source clarification. The source now names SREV-334, describes the
window-station clipboard, UIPI/MIC integrity labels, private clipboard item
layout probe, and out-of-sandbox reader bridge. It also labels
`win32k!FindClipFormat` as private observation rather than API contract. No
offset, item-length scan, integrity-index scan, service-only caller gate,
delayed-rendering drain, or rewrite predicate changed.

## Acceptance Gate

`docs/plan/check-srev-334.py` validates the draft-07 schema, official
references, source comment ownership, Vista+ and service-only gates,
`Dyndata_Config.Clipboard_offset`, sentinel item-layout probe, known-integrity
rewrite gate, `CloseClipboardSlave` delayed-rendering drain, stale
bug/workaround wording removal, combined ledger entry, and split ledger
fragment.

Runtime gate: Windows clipboard matrix covering UAC/UIPI on and off, sandbox to
host copy/paste, host to sandbox copy/paste, delayed rendering formats,
Office/Excel `WM_RENDERFORMAT` behavior, multiple clipboard formats, and
Windows versions with changed private clipboard item layout.
