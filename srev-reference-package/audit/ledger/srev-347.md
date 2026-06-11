---
kind: srev-ledger-entry
id: SREV-347
title: GUI DDE ACK Proxy Window Validation
status: patched-source-level-after-official-dde-window-handle-review-needs-windows-runtime-proof
owner: Sandboxie/core/svc/GuiServer.cpp
spec: docs/plan/srev-347-gui-dde-ack-proxy-window-validation.md
schema: docs/plan/srev-347-gui-dde-ack-proxy-window-validation.schema.json
checker: docs/plan/check-srev-347.py
runtime_gate: Windows SbieSvc and DLL build with direct DDE SendMessage proxy smoke, stale client HWND no-proxy proof, and SendMessageTimeout normal broker proof
---

### SREV-347: GUI DDE ACK Proxy Window Validation

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | patched source-level after official DDE/window-handle review; needs Windows runtime proof |
| Evidence | Microsoft documents DDE as a window-message protocol where a DDE conversation is identified by the client/server window pair, and documents `WM_DDE_ACK` for initiation as a `SendMessage` path. Locally, `Gui_SendMessageA/W` call `Gui_DDE_ACK_Sending` for `WM_DDE_ACK` and then send `GUI_SEND_POST_MESSAGE` with `which` set to `'sm a'` or `'sm w'`. `Gui_SendMessageTimeoutA/W` use `'smta'` and `'smtw'` and do not call `Gui_DDE_ACK_Sending`. Before this SREV, `GuiServer::SendPostMessageSlave` named timeout `which` values in the DDE proxy startup branch and, because of C operator precedence, applied `IsWindow(hwnd)` to `'sm a'` but not to `'sm w'`. |
| Data | `Gui_SendMessageA`, `Gui_SendMessageW`, `Gui_SendMessageTimeoutA`, `Gui_SendMessageTimeoutW`, `Gui_DDE_ACK_Sending`, `GUI_SEND_POST_MESSAGE`, `GUI_SEND_POST_MESSAGE_REQ.which`, `WM_DDE_ACK`, `IsWindow`, `DdeProxyThreadSlave`, client HWND, server HWND, and initial ACK `lParam`. |
| Schema | `GUI_DDE_ACK_PROXY_WINDOW_VALIDATION` says DDE conversation identity is a pair of participating window handles; DDE ACK proxy startup is for direct `SendMessageA/W`; `SendMessageTimeoutA/W` stays on the normal timeout broker path; `SendPostMessageSlave` validates the client HWND with `IsWindow` before allocating proxy arguments or creating `DdeProxyThreadSlave`; SREV-084 owns DDE ACK `lParam` forwarding and SREV-293 owns the `guidde.c` topology comment. |
| Topology | `sandboxed DDE server -> Gui_SendMessageA/W(WM_DDE_ACK) -> Gui_DDE_ACK_Sending restores real client HWND when needed -> GUI_SEND_POST_MESSAGE which='sm a'/'sm w' -> GuiServer::SendPostMessageSlave -> IsWindow(client HWND) -> DdeProxyThreadSlave -> SbieSvc DDE proxy window -> initial SendMessage(client HWND, WM_DDE_ACK, proxy HWND, lParam) -> posted DDE bridge`. |
| Logic Risk | Unicode `SendMessageW` could start a proxy thread for a stale or invalid client HWND because the `IsWindow` guard did not apply to the `'sm w'` branch. The timeout `which` values in the outer condition also implied that timeout sends might start the DDE proxy even though the local DLL never performs the DDE ACK conversation mapping for `SendMessageTimeoutA/W`. |
| Official Shape | Microsoft documents DDE conversation identity as window-pair topology, initiation ACK as a `SendMessage` path, `SendMessage` as a synchronous window-procedure call, `SendMessageTimeout` as a separate timeout-capable send API, and `IsWindow` as a point-in-time window-handle existence check. |
| Fix | `SendPostMessageSlave` now starts the DDE ACK proxy only for direct `SendMessageA/W` requests and applies `IsWindow(hwnd)` before allocating proxy arguments or creating `DdeProxyThreadSlave`. No DDE `lParam` forwarding, `WM_COPYDATA` bridge, `DDE_Request_ProxyWnd`, timeout send behavior, OpenWinClass access checks, or general `SendMessageTimeoutA/W` broker behavior changed. |
| Acceptance Gate | `docs/plan/check-srev-347.py` validates the draft-07 schema, official references, local direct-send / timeout routing evidence, `IsWindow` ordering before `HeapAlloc` and `CreateThread`, stale branch-shape removal, DDE proxy topology preservation, combined ledger entry, and split ledger fragment; `docs/plan/check-srev-347.sh` is the targeted wrapper. Runtime gate: Windows SbieSvc/DLL build plus DDE smoke proving external client to sandboxed server DDE initiation still creates the proxy for direct `SendMessageA/W`, invalid/stale client HWND does not create a useless proxy thread, and `SendMessageTimeoutA/W` keeps its normal timeout broker behavior. |
