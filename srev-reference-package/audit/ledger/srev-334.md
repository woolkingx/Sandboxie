---
kind: srev-ledger-entry
id: SREV-334
title: GUI Clipboard Integrity Bridge
status: patched-comment-topology-after-official-clipboard-window-station-mic-review-no-behavior-change
owner: Sandboxie/core/drv/gui.c
spec: docs/plan/srev-334-gui-clipboard-il-bridge.md
schema: docs/plan/srev-334-gui-clipboard-il-bridge.schema.json
checker: docs/plan/check-srev-334.py
runtime_gate: Windows clipboard matrix for UAC UIPI delayed rendering and private item layout changes
---

### SREV-334: GUI Clipboard Integrity Bridge

| Field | Content |
|---|---|
| Severity | [medium] |
| Status | patched comment/topology after official clipboard, window-station, MIC, and UIPI review; no behavior change |
| Evidence | `Gui_Api_Clipboard` references the current process window station, reaches the private clipboard item area through `Dyndata_Config.Clipboard_offset`, learns item length and integrity-index slot from four sentinel formats, rewrites known MIC labels, and rejects non-service callers because the driver does not own clipboard locking. `GuiServer::CloseClipboardSlave` opens the clipboard, calls `API_GUI_CLIPBOARD`, forces delayed rendering with `EnumClipboardFormats` / `GetClipboardData`, and closes the clipboard. The old driver comment framed this as a Windows bug workaround rather than a private-layout bridge. |
| Data | `API_GUI_CLIPBOARD`, `Gui_Api_Clipboard`, `Gui_ReferenceClipboard`, `PsGetProcessWin32WindowStation`, `ExWindowStationObjectType`, `Dyndata_Config.Clipboard_offset`, `Gui_InitClipboard`, `Gui_FixClipboard`, `Gui_ClipboardItemLength`, `Gui_ClipboardIntegrityIndex`, sentinel formats `0x111111` through `0x444444`, MIC values `0x0000` through `0x4000`, `CloseClipboardSlave`, `OpenClipboard`, `EnumClipboardFormats`, `GetClipboardData`, and `CloseClipboard`. |
| Schema | `GUI_CLIPBOARD_INTEGRITY_BRIDGE` says the public clipboard API owns open/close, ownership, delayed rendering, and format enumeration; the window station owns the documented clipboard container; `Gui_Api_Clipboard` is service-only because the driver does not own clipboard locking; `Gui_InitClipboard` owns only the private runtime-probed clipboard item layout; `Gui_FixClipboard` rewrites only known MIC integrity label slots after the layout probe succeeds; `win32k!FindClipFormat` names private observation evidence and not public API contract; this SREV changes comments and proof only. |
| Topology | `Gui_CloseClipboard in sandboxed DLL -> SbieSvc CloseClipboardSlave -> OpenClipboard / delayed-rendering drain -> API_GUI_CLIPBOARD service-only driver call -> current window-station clipboard private item area -> integrity label rewrite`. Init path: `Gui_InitClipboard -> Dyndata_Config.Clipboard_offset -> sentinel formats -> item length and integrity index`. Fix path: `Gui_FixClipboard -> known MIC labels -> integrity slot rewrite`. |
| Logic Risk | Treating a private win32k observation as API truth could lead future patches to hard-code a new item layout, call the API without the service-held clipboard lock, or widen the caller gate. The correct split keeps official clipboard/window-station APIs as public protocol and Sandboxie's dynamic probe as a private runtime schema for the current Windows build. |
| Official Shape | Microsoft documents clipboard open/close, ownership, delayed rendering, and format enumeration; a window station contains a clipboard and requires `WINSTA_ACCESSCLIPBOARD`; Mandatory Integrity Control assigns integrity levels to principals and securable objects; UIPI blocks UI messages from lower-integrity senders unless filters allow them. |
| Fix | Comment-only source clarification. The source now names SREV-334, describes the window-station clipboard, UIPI/MIC integrity labels, private clipboard item layout probe, and out-of-sandbox reader bridge. It also labels `win32k!FindClipFormat` as private observation rather than API contract. No offset, item-length scan, integrity-index scan, service-only caller gate, delayed-rendering drain, or rewrite predicate changed. |
| Acceptance Gate | `docs/plan/check-srev-334.py` validates the draft-07 schema, official references, source comment ownership, Vista+ and service-only gates, `Dyndata_Config.Clipboard_offset`, sentinel item-layout probe, known-integrity rewrite gate, `CloseClipboardSlave` delayed-rendering drain, stale bug/workaround wording removal, combined ledger entry, and split ledger fragment; `docs/plan/check-srev-334.sh` is the targeted wrapper. Runtime gate: Windows clipboard matrix covering UAC/UIPI on and off, sandbox to host copy/paste, host to sandbox copy/paste, delayed rendering formats, Office/Excel `WM_RENDERFORMAT` behavior, multiple clipboard formats, and Windows versions with changed private clipboard item layout. |
