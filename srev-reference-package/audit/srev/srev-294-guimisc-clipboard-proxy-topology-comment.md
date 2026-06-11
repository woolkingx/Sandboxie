# SREV-294: GuiMisc Clipboard Proxy Topology Comment

## Stage Gate

| Field | Value |
|---|---|
| Stage | schema -> boundary -> topology -> verify |
| Input artifact | `Sandboxie/core/dll/guimisc.c`, `Sandboxie/core/svc/GuiServer.cpp`, `Sandboxie/core/drv/gui.c`, SREV-096, SREV-134, Microsoft clipboard/listener/MIC references |
| Output artifact | Source comment owner, draft-07 schema, targeted checker, ledger fragment |
| Owner | `guimisc.c` clipboard support topology comment and `Gui_CloseClipboard` proxy edge |
| Acceptance gate | Targeted checker validates source comment, official references, user-mode close edge, SbieSvc/driver adjacency, SREV-096/SREV-134 adjacency, stale bug/direction wording removal, and ledger fragment |

## Data

`guimisc.c` owns the user-mode clipboard hook wrappers. The relevant source
edge is:

```text
sandboxed process opens/closes clipboard
  -> Gui_OpenClipboard records sequence number and owner thread
  -> Gui_CloseClipboard detects sequence change
  -> Gui_CallProxyEx(GUI_CLOSE_CLIPBOARD)
  -> SbieSvc CloseClipboardSlave
  -> delayed-rendering force and API_GUI_CLIPBOARD integrity rewrite
```

The old comment said an outside process copies data with integrity level zero,
then an outside process cannot paste. The driver-side SREV-096 evidence shows
the intended direction more precisely: data copied by a sandboxed process can
carry clipboard item integrity that blocks the outside reader, and SbieSvc asks
the driver to rewrite the private clipboard item integrity.

## Official Shape

Microsoft documents clipboard operations around `OpenClipboard`,
`CloseClipboard`, `SetClipboardData`, `GetClipboardData`, delayed rendering,
and clipboard ownership.

Microsoft documents `SetClipboardViewer` as an old clipboard viewer-chain API
where viewers receive `WM_DRAWCLIPBOARD`, and says newer applications should use
the clipboard sequence number or clipboard format listener registration.

Microsoft documents `AddClipboardFormatListener` as registering a window to
receive posted `WM_CLIPBOARDUPDATE` messages whenever clipboard contents change.

Microsoft documents Mandatory Integrity Control as assigning integrity levels
to principals and securable objects. That is the public security model behind
the local private-layout clipboard rewrite; the private win32k clipboard item
layout remains undocumented.

Official references:

- `https://learn.microsoft.com/en-us/windows/win32/dataxchg/clipboard-operations`
- `https://learn.microsoft.com/en-us/windows/win32/dataxchg/clipboard`
- `https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setclipboardviewer`
- `https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-addclipboardformatlistener`
- `https://learn.microsoft.com/en-us/windows/win32/dataxchg/wm-clipboardupdate`
- `https://learn.microsoft.com/en-us/windows/win32/secauthz/mandatory-integrity-control`

## Schema

Local schema:

```text
docs/plan/srev-294-guimisc-clipboard-proxy-topology-comment.schema.json
```

Contract id:

```text
GUIMISC_CLIPBOARD_PROXY_TOPOLOGY_COMMENT
```

## Boundary

```text
user-mode clipboard close
  -> DLL hook in guimisc.c
  -> SbieSvc GUI proxy
  -> driver API_GUI_CLIPBOARD
  -> private clipboard item integrity rewrite
```

`guimisc.c` owns deciding when to call the proxy after a clipboard sequence
change. SbieSvc owns the open/close/delayed-rendering proxy path. The driver
owns private clipboard item layout discovery and integrity rewriting, already
covered by SREV-096 and SREV-134.

## Topology

```text
Gui_OpenClipboard
  -> records `Gui_OpenClipboard_seq`

Gui_CloseClipboard
  -> real CloseClipboard
  -> GetClipboardSequenceNumber
  -> if changed on Vista+
  -> Gui_CallProxyEx(GUI_CLOSE_CLIPBOARD)

GuiServer::CloseClipboardSlave
  -> OpenClipboard
  -> API_GUI_CLIPBOARD(0x4000)
  -> EnumClipboardFormats / GetClipboardData delayed-rendering
  -> API_GUI_CLIPBOARD(caller_il)
  -> CloseClipboard

SbieDrv Gui_Api_Clipboard
  -> SREV-096 reference-scoped window-station/private-clipboard access
```

## Logic Risk

The old comment framed the issue as a possible win32k bug and did not name the
owner split. That can push future work toward private win32k layout assumptions
instead of preserving the documented clipboard close/delayed-rendering edge and
the already-reviewed driver object-reference gate.

There is still an open runtime race noted in the existing source: clipboard
viewer or format-listener notification can observe a clipboard change before
SbieSvc finishes the integrity fix. This SREV does not change that behavior; it
keeps the race visible and ties it to the runtime gate.

## Fix

Comment-only source clarification. The source now names SREV-294, fixes the
direction of the integrity problem, separates public clipboard/MIC concepts
from private win32k layout observation, and points the driver-side owner to
SREV-096. No `OpenClipboard`, `CloseClipboard`, sequence-number check,
`Gui_CallProxyEx`, delayed-rendering, SbieSvc, or driver behavior changed.

## Acceptance Gate

`docs/plan/check-srev-294.py` validates the draft-07 schema, official
references, source comment, stale bug/direction wording removal,
`Gui_CloseClipboard` proxy edge, SbieSvc `CloseClipboardSlave`, driver
`API_GUI_CLIPBOARD`, SREV-096/SREV-134 adjacency, combined ledger entry, and
split ledger fragment.

Runtime gate: inherited Windows Vista+ clipboard matrix from SREV-096 plus
explicit viewer/listener notification race observation for `SetClipboardViewer`
and `AddClipboardFormatListener` paths.
