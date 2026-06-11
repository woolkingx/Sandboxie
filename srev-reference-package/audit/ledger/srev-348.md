---
kind: srev-ledger-entry
id: SREV-348
title: GUI DDE DATA Proxy Route Map
status: patched-source-level-after-official-dde-request-data-route-review-needs-windows-runtime-proof
owner: Sandboxie/core/svc/GuiServer.cpp
spec: docs/plan/srev-348-gui-dde-data-proxy-route-map.md
schema: docs/plan/srev-348-gui-dde-data-proxy-route-map.schema.json
checker: docs/plan/check-srev-348.py
runtime_gate: Windows SbieSvc and DLL build with two overlapping DDE request/data replies returning through their own proxy windows and missing-route failure proof
---

### SREV-348: GUI DDE DATA Proxy Route Map

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official DDE request/data route review; needs Windows runtime proof |
| Evidence | `GuiServer::SendCopyDataSlave` had a comment saying cross-sandbox DDE `WM_DDE_REQUEST` / `WM_DDE_DATA` exchange used a global variable hack to remember the `DdeProxyThreadSlave` proxy window. Microsoft documents DDE as a window-message protocol where a server responds to `WM_DDE_REQUEST` by posting `WM_DDE_DATA`, and documents `WM_DDE_DATA` lParam high word as the atom identifying the data item. Locally, `Gui_DDE_DATA_Posting` already sends the real client HWND in `GUI_SEND_COPYDATA_REQ.hwnd` and the DDE item atom in `cds_key`, while `DdeProxyThreadSlave` can unpack the item atom from the earlier `WM_DDE_REQUEST`. |
| Data | `DdeProxyThreadSlave`, `SendCopyDataSlave`, `Gui_DDE_DATA_Posting`, `GUI_SEND_COPYDATA_REQ.hwnd`, `GUI_SEND_COPYDATA_REQ.cds_key`, real client HWND, SbieSvc proxy HWND, `WM_DDE_REQUEST`, `WM_DDE_DATA`, `PackDDElParam`, `UnpackDDElParam`, and private `WM_USER + 0x123` proxy-thread hop. |
| Schema | `GUI_DDE_DATA_PROXY_ROUTE_MAP` says DDE request/data replies are routed by pending request identity rather than by one process-global proxy HWND; the route key is real client HWND plus the DDE item atom carried by `WM_DDE_REQUEST` and `WM_DDE_DATA`; `DdeProxyThreadSlave` extracts the request item atom with `UnpackDDElParam`; `Gui_DDE_DATA_Posting` sends the real client HWND and data item atom through `GUI_SEND_COPYDATA`; `SendCopyDataSlave` takes and removes the matching route before posting the private DDE DATA hop. |
| Topology | `DdeProxyThreadSlave receives WM_DDE_REQUEST -> UnpackDDElParam(WM_DDE_REQUEST) extracts DDE item atom -> Dde_SetRequestProxyWnd(real client HWND, item atom, SbieSvc proxy HWND) -> SendMessage(WM_COPYDATA) to sandbox server -> sandbox server posts WM_DDE_DATA -> Gui_DDE_DATA_Posting extracts WM_DDE_DATA item atom -> GUI_SEND_COPYDATA which='dde ', hwnd=real client HWND, cds_key=item atom -> SendCopyDataSlave Dde_TakeRequestProxyWnd(real client HWND, item atom) -> private PostMessage to matched SbieSvc proxy window -> DdeProxyThreadSlave posts WM_DDE_DATA to real client`. |
| Logic Risk | A single process-global proxy HWND can be overwritten by another DDE proxy thread before the matching `WM_DDE_DATA` reply arrives. That can route data to the wrong proxy thread, drop a valid reply after another thread clears the global, or make overlapping item requests depend on timing rather than protocol identity. |
| Official Shape | Microsoft documents DDE request/data reply semantics, `WM_DDE_DATA` item atom identity, DDE lParam helper ownership, and `PostMessage` queue routing. Those shapes require the private SbieSvc hop to target the proxy window for the corresponding pending request, not the last request seen by the service process. |
| Fix | `GuiServer.cpp` now stores pending DDE request routes in a small service-local map keyed by real client HWND and DDE item atom. `DdeProxyThreadSlave` records the route after unpacking `WM_DDE_REQUEST`; `SendCopyDataSlave` takes and removes the matching route before posting the private `WM_USER + 0x123` hop to the owning proxy window. Stale single-HWND route state and the global-variable-hack comment were removed. |
| Acceptance Gate | `docs/plan/check-srev-348.py` validates the draft-07 schema, official references, local `WM_DDE_REQUEST` / `WM_DDE_DATA` item atom shape, the service-local route map, route set/take locking, stale single-HWND global removal, `SendCopyDataSlave` lookup by real client HWND plus `cds_key`, `DdeProxyThreadSlave` route registration by unpacked item atom, combined ledger entry, and split ledger fragment; `docs/plan/check-srev-348.sh` is the targeted wrapper. Runtime gate: Windows SbieSvc/DLL build plus DDE request/data smoke with two overlapping external-client to sandbox-server DDE item requests proving each `WM_DDE_DATA` returns through its own SbieSvc proxy window and stale/missing route returns failure without posting to an unrelated proxy. |
