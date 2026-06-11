---
kind: srev-ledger-entry
id: SREV-346
title: GUI Clipboard Metafile Policy Gate
status: patched-source-level-after-official-clipboard-policy-review-needs-windows-runtime-proof
owner: Sandboxie/core/svc/GuiServer.cpp
spec: docs/plan/srev-346-gui-clipboard-metafile-policy-gate.md
schema: docs/plan/srev-346-gui-clipboard-metafile-policy-gate.schema.json
checker: docs/plan/check-srev-346.py
runtime_gate: Windows SbieSvc and DLL build with OpenClipboard=n denied CF_METAFILEPICT broker read and OpenClipboard=y ordinary plus metafile clipboard smoke
---

### SREV-346: GUI Clipboard Metafile Policy Gate

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official clipboard/window-station policy review; needs Windows runtime proof |
| Evidence | `GuiServer::GetClipboardDataSlave` already queries the caller's box and denies service-side clipboard reads when `OpenClipboard=n`. `Gui_GetClipboardData_MF` makes a secondary `GUI_GET_CLIPBOARD_METAFILE` request for `CF_METAFILEPICT` because the first broker reply contains a `METAFILEPICT` whose `hMF` is valid in the SbieSvc context. Before this SREV, `GuiServer::GetClipboardMetaFileSlave` carried a TODO to fail when the calling process should not have clipboard access, but it opened the clipboard and read `CF_METAFILEPICT` without enforcing the box setting. |
| Data | `Gui_GetClipboardData`, `Gui_GetClipboardData_MF`, `GUI_GET_CLIPBOARD_DATA`, `GUI_GET_CLIPBOARD_METAFILE`, `GUI_GET_CLIPBOARD_DATA_REQ`, `GUI_GET_CLIPBOARD_DATA_RPL`, `GuiServer::GetClipboardDataSlave`, `GuiServer::GetClipboardMetaFileSlave`, `SbieApi_QueryProcess`, `SbieApi_QueryConfBool`, `OpenClipboard`, `ERROR_ACCESS_DENIED`, `CF_METAFILEPICT`, `METAFILEPICT`, `GlobalLock`, `GetMetaFileBitsEx`, and `GetClipboardDataSlave2`. |
| Schema | `GUI_CLIPBOARD_METAFILE_POLICY_GATE` says `OpenClipboard` is a Sandboxie box policy for clipboard access; `GetClipboardDataSlave` enforces `OpenClipboard` before opening the clipboard; `GetClipboardMetaFileSlave` is a secondary `CF_METAFILEPICT` read broker and must enforce the same policy; the denied path returns `GUI_GET_CLIPBOARD_DATA_RPL` with `result = 0` and `ERROR_ACCESS_DENIED`; `GetClipboardMetaFileSlave` must not call `OpenClipboard(NULL)` before the policy check passes; allowed callers preserve the existing `CF_METAFILEPICT` `GetClipboardData` / `GlobalLock` / `GetMetaFileBitsEx` / section-copy topology; Windows runtime proof is still required. |
| Topology | `sandboxed process -> Gui_GetClipboardData(CF_METAFILEPICT) -> OpenClipboard setting check in DLL -> GUI_GET_CLIPBOARD_DATA -> GuiServer::GetClipboardDataSlave OpenClipboard setting check -> section containing METAFILEPICT -> Gui_GetClipboardData_MF -> GUI_GET_CLIPBOARD_METAFILE -> GuiServer::GetClipboardMetaFileSlave OpenClipboard setting check -> OpenClipboard(NULL) -> GetClipboardData(CF_METAFILEPICT) -> GlobalLock(METAFILEPICT) -> GetMetaFileBitsEx(hMF) -> GetClipboardDataSlave2 duplicate read-only section`. |
| Logic Risk | Without the service-side policy gate, a sandbox configured with `OpenClipboard=n` could still use the `GUI_GET_CLIPBOARD_METAFILE` secondary path after a `CF_METAFILEPICT` broker flow reached `Gui_GetClipboardData_MF`. That bypasses the setting intent and creates a policy asymmetry: ordinary clipboard formats are denied by the service broker, while classic metafile bytes are still read through the service. |
| Official Shape | Microsoft documents the clipboard as a shared data-transfer facility, `OpenClipboard` as the open/lock edge, `GetClipboardData` as requiring a previously opened clipboard and returning a clipboard-owned handle that must be copied immediately, and window stations as containing a clipboard with `WINSTA_ACCESSCLIPBOARD` governing clipboard use. |
| Fix | `GetClipboardMetaFileSlave` now queries the calling process box, reads `OpenClipboard`, and returns `ERROR_ACCESS_DENIED` in the normal `GUI_GET_CLIPBOARD_DATA_RPL` shape before entering the clipboard critical section or calling `OpenClipboard(NULL)`. No `CF_METAFILEPICT` validation, `OpenClipboard`/`CloseClipboard` pairing, `GetClipboardData`, `GlobalLock`/`GlobalUnlock`, `GetMetaFileBitsEx`, section-copy, or handle-duplication behavior changed for allowed callers. |
| Acceptance Gate | `docs/plan/check-srev-346.py` validates the draft-07 schema, official references, ordinary clipboard broker policy adjacency, the new metafile policy gate, denied-path reply shape, policy-before-open ordering, preservation of the existing `CF_METAFILEPICT` copy topology, stale TODO removal, combined ledger entry, and split ledger fragment; `docs/plan/check-srev-346.sh` is the targeted wrapper. Runtime gate: Windows SbieSvc/DLL build and clipboard smoke with `OpenClipboard=n` proving `CF_METAFILEPICT` broker reads return access denied without opening the clipboard, plus `OpenClipboard=y` proof that ordinary clipboard reads and `CF_METAFILEPICT` metafile paste still work. |
