# SREV-346: GUI Clipboard Metafile Policy Gate

| Field | Content |
|---|---|
| Stage | schema -> boundary -> topology -> action -> verify |
| Input artifact | `Sandboxie/core/svc/GuiServer.cpp`, `Sandboxie/core/dll/guimisc.c`, `Sandboxie/core/svc/GuiWire.h`, `Sandboxie/install/SbieSettings.ini`, SREV-096, SREV-334, and Microsoft clipboard/window-station documentation |
| Output artifact | Source patch, draft-07 schema, checker, and ledger fragment |
| Owner | `GuiServer::GetClipboardMetaFileSlave` secondary `CF_METAFILEPICT` broker path |
| Acceptance gate | Targeted checker validates official references, `OpenClipboard` policy inheritance, denied-path reply shape, no clipboard open before policy check, existing metafile copy topology, and ledger fragment |

## Data

`Gui_GetClipboardData` first blocks direct clipboard reads when
`OpenClipboard=n`. If a direct system `GetClipboardData` fails with
`ERROR_ACCESS_DENIED` or `ERROR_INVALID_HANDLE`, it asks SbieSvc through
`GUI_GET_CLIPBOARD_DATA`. `GuiServer::GetClipboardDataSlave` already enforces
the box-level `OpenClipboard` setting before opening the host clipboard.

`CF_METAFILEPICT` needs a second service call. The first data call returns a
`METAFILEPICT` structure whose `hMF` is valid in the SbieSvc context. The DLL
therefore calls `GUI_GET_CLIPBOARD_METAFILE`, and
`GuiServer::GetClipboardMetaFileSlave` opens the clipboard, gets the
`CF_METAFILEPICT` handle, locks the structure, extracts the `HMETAFILE` bytes,
copies those bytes into a section, and duplicates the section handle back to the
sandboxed process.

Before this SREV, the metafile helper carried a `todo` saying it should fail if
the calling process should not have clipboard access. The ordinary clipboard
data broker had the `OpenClipboard` policy gate; the secondary metafile broker
did not.

## Official Shape

Microsoft documents the clipboard as a shared data-transfer facility and warns
that it should not be used for sensitive data. `OpenClipboard` opens the
clipboard for examination and prevents other applications from modifying its
content; callers should call `CloseClipboard` after every successful open.
`GetClipboardData` requires a previously opened clipboard and returns a
clipboard-owned handle that the application must copy immediately, must not
free, must not leave locked, and must not use after `CloseClipboard`,
`EmptyClipboard`, or replacement with `SetClipboardData`.

Microsoft documents a window station as containing a clipboard, atom table, and
desktop objects. `WINSTA_ACCESSCLIPBOARD` is the window-station access right for
clipboard use.

Official references:

- `https://learn.microsoft.com/en-us/windows/win32/dataxchg/clipboard`
- `https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-openclipboard`
- `https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-getclipboarddata`
- `https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-closeclipboard`
- `https://learn.microsoft.com/en-us/windows/win32/winstation/about-window-stations-and-desktops`
- `https://learn.microsoft.com/en-us/windows/win32/winstation/window-station-security-and-access-rights`

## Boundary

`OpenClipboard` is a Sandboxie box policy. The user-mode DLL checks it before
asking for clipboard data. The service broker must also enforce it because the
broker executes the host-side clipboard open/read edge on behalf of a sandboxed
process.

`GetClipboardMetaFileSlave` is not an independent permission owner. It is a
secondary clipboard-read helper for `CF_METAFILEPICT` and must inherit the same
policy gate as `GetClipboardDataSlave`.

## Topology

```text
sandboxed process
  -> Gui_GetClipboardData(CF_METAFILEPICT)
  -> OpenClipboard setting check in DLL
  -> GUI_GET_CLIPBOARD_DATA
  -> GuiServer::GetClipboardDataSlave OpenClipboard setting check
  -> section containing METAFILEPICT
  -> Gui_GetClipboardData_MF
  -> GUI_GET_CLIPBOARD_METAFILE
  -> GuiServer::GetClipboardMetaFileSlave OpenClipboard setting check
  -> OpenClipboard(NULL)
  -> GetClipboardData(CF_METAFILEPICT)
  -> GlobalLock(METAFILEPICT)
  -> GetMetaFileBitsEx(hMF)
  -> GetClipboardDataSlave2 duplicate read-only section
```

Denied path:

```text
OpenClipboard=n
  -> rpl->result = 0
  -> rpl->error = ERROR_ACCESS_DENIED
  -> no OpenClipboard(NULL)
  -> GUI_GET_CLIPBOARD_METAFILE returns STATUS_SUCCESS transport reply
```

## Logic Risk

Without the service-side policy gate, a sandbox configured with
`OpenClipboard=n` could still use the `GUI_GET_CLIPBOARD_METAFILE` secondary
path after a `CF_METAFILEPICT` broker flow reached `Gui_GetClipboardData_MF`.
That bypasses the setting intent and creates a policy asymmetry: ordinary
clipboard formats are denied by the service broker, while classic metafile
bytes are still read through the service.

## Fix

`GetClipboardMetaFileSlave` now queries the calling process box, reads
`OpenClipboard`, and returns `ERROR_ACCESS_DENIED` in the normal
`GUI_GET_CLIPBOARD_DATA_RPL` shape before entering the clipboard critical
section or calling `OpenClipboard(NULL)`.

No `CF_METAFILEPICT` validation, `OpenClipboard`/`CloseClipboard` pairing,
`GetClipboardData`, `GlobalLock`/`GlobalUnlock`, `GetMetaFileBitsEx`,
section-copy, or handle-duplication behavior changed for allowed callers.

## Acceptance Gate

`docs/plan/check-srev-346.py` validates the draft-07 schema, official
references, ordinary clipboard broker policy adjacency, the new metafile
policy gate, denied-path reply shape, policy-before-open ordering, preservation
of the existing `CF_METAFILEPICT` copy topology, stale TODO removal, combined
ledger entry, and split ledger fragment.

Runtime gate: Windows SbieSvc/DLL build and clipboard smoke with
`OpenClipboard=n` proving `CF_METAFILEPICT` broker reads return access denied
without opening the clipboard, plus `OpenClipboard=y` proof that ordinary
clipboard reads and `CF_METAFILEPICT` metafile paste still work.
