---
kind: srev-ledger-entry
id: SREV-294
title: GuiMisc Clipboard Proxy Topology Comment
status: patched-comment-topology-after-official-clipboard-mic-and-srev-096-review-no-behavior-change
owner: Sandboxie/core/dll/guimisc.c
spec: docs/plan/srev-294-guimisc-clipboard-proxy-topology-comment.md
schema: docs/plan/srev-294-guimisc-clipboard-proxy-topology-comment.schema.json
checker: docs/plan/check-srev-294.py
runtime_gate: SREV-096 Windows Vista+ clipboard matrix plus SetClipboardViewer and AddClipboardFormatListener notification race observation
---

### SREV-294: GuiMisc Clipboard Proxy Topology Comment

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | patched comment/topology after official clipboard, Mandatory Integrity Control, and SREV-096 review; no behavior change |
| Evidence | `guimisc.c` owns user-mode clipboard hook wrappers. `Gui_OpenClipboard` records the clipboard sequence number and owner thread. `Gui_CloseClipboard` closes the real clipboard, detects sequence change, and calls SbieSvc through `GUI_CLOSE_CLIPBOARD`. The old comment said an outside process copies data with integrity level zero, then an outside process cannot paste. SREV-096 shows the intended direction more precisely: data copied by a sandboxed process can carry clipboard item integrity that blocks the outside reader, and SbieSvc asks the driver to rewrite the private clipboard item integrity. |
| Data | `Gui_OpenClipboard`, `Gui_CloseClipboard`, `GetClipboardSequenceNumber`, `GUI_CLOSE_CLIPBOARD`, `GuiServer::CloseClipboardSlave`, `OpenClipboard`, `EnumClipboardFormats`, `GetClipboardData`, `API_GUI_CLIPBOARD`, `drv/gui.c`, `Gui_FixClipboard`, clipboard item integrity, `SetClipboardViewer`, `AddClipboardFormatListener`, SREV-096, and SREV-134. |
| Schema | `GUIMISC_CLIPBOARD_PROXY_TOPOLOGY_COMMENT` says `guimisc.c` owns the user-mode `CloseClipboard` hook decision to call SbieSvc after a sequence change; SbieSvc GUI Proxy owns delayed-rendering force and `API_GUI_CLIPBOARD` calls; `drv/gui.c` owns private clipboard item layout discovery and integrity rewrite; private win32k clipboard layout is observation evidence, not API contract; SREV-096 owns driver-side window-station reference and integrity rewrite gates; SREV-134 owns service-side clipboard probe data shape; clipboard viewer/listener race remains a Windows runtime gate; this SREV changes comments and proof only. |
| Topology | `Gui_OpenClipboard -> record Gui_OpenClipboard_seq`; `Gui_CloseClipboard -> real CloseClipboard -> GetClipboardSequenceNumber -> if changed on Vista+ -> Gui_CallProxyEx(GUI_CLOSE_CLIPBOARD)`; `GuiServer::CloseClipboardSlave -> OpenClipboard -> API_GUI_CLIPBOARD(0x4000) -> EnumClipboardFormats / GetClipboardData delayed-rendering -> API_GUI_CLIPBOARD(caller_il) -> CloseClipboard`; `SbieDrv Gui_Api_Clipboard -> SREV-096 reference-scoped window-station/private-clipboard access`. |
| Logic Risk | The old comment framed the issue as a possible win32k bug and did not name the owner split. That can push future work toward private win32k layout assumptions instead of preserving the documented clipboard close/delayed-rendering edge and the already-reviewed driver object-reference gate. The existing viewer/listener notification race is still open runtime behavior, not closed by this comment patch. |
| Official Shape | Microsoft documents clipboard operations around `OpenClipboard`, `CloseClipboard`, `SetClipboardData`, `GetClipboardData`, delayed rendering, and clipboard ownership. Microsoft documents `SetClipboardViewer` as an old viewer-chain API and `AddClipboardFormatListener` / `WM_CLIPBOARDUPDATE` as the Vista+ listener path. Microsoft documents Mandatory Integrity Control as assigning integrity levels to principals and securable objects. |
| Fix | Comment-only source clarification. The source now names SREV-294, fixes the direction of the integrity problem, separates public clipboard/MIC concepts from private win32k layout observation, and points the driver-side owner to SREV-096. No `OpenClipboard`, `CloseClipboard`, sequence-number check, `Gui_CallProxyEx`, delayed-rendering, SbieSvc, or driver behavior changed. |
| Acceptance Gate | `docs/plan/check-srev-294.py` validates the draft-07 schema, official references, source comment, stale bug/direction wording removal, `Gui_CloseClipboard` proxy edge, SbieSvc `CloseClipboardSlave`, driver `API_GUI_CLIPBOARD`, SREV-096/SREV-134 adjacency, combined ledger entry, and split ledger fragment; `docs/plan/check-srev-294.sh` is the targeted wrapper. Runtime gate: inherited Windows Vista+ clipboard matrix from SREV-096 plus explicit viewer/listener notification race observation for `SetClipboardViewer` and `AddClipboardFormatListener` paths. |
