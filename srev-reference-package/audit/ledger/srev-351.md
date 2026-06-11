---
kind: srev-ledger-entry
id: SREV-351
title: GUI DDE Service Proxy Topology Comment
status: patched-comment-topology-after-official-dde-and-wm-copydata-review-no-behavior-change
owner: Sandboxie/core/svc/GuiServer.cpp
spec: docs/plan/srev-351-gui-dde-service-proxy-topology-comment.md
schema: docs/plan/srev-351-gui-dde-service-proxy-topology-comment.schema.json
checker: docs/plan/check-srev-351.py
runtime_gate: none for comment-only clarification; inherited Windows DDE runtime gates remain SREV-084, SREV-347, and SREV-348
---

### SREV-351: GUI DDE Service Proxy Topology Comment

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | patched comment/topology after official DDE and `WM_COPYDATA` review; no behavior change |
| Evidence | `DdeProxyThreadSlave` creates the SbieSvc-side proxy window used by the DDE bridge. The local comment still described this as needed because of an `IL bug in core/dll/guidde.c`. SREV-293 already reframed the `guidde.c` side as restricted-token / UIPI posted-DDE compatibility topology, where private win32k observations are evidence rather than API contract. Microsoft documents DDE as a window-message protocol, `WM_DDE_EXECUTE` and `WM_DDE_REQUEST` as posted DDE messages, posted DDE `lParam` helpers, and `WM_COPYDATA` as `SendMessage`-only data valid during message processing. |
| Data | `DdeProxyThreadSlave`, `_DDE_ProxyClass2`, real client HWND, sandbox server HWND, service proxy HWND, `WM_DDE_ACK`, `WM_DDE_EXECUTE`, `WM_DDE_REQUEST`, `WM_DDE_DATA`, `WM_COPYDATA`, `PackDDElParam`, `UnpackDDElParam`, SREV-084, SREV-293, SREV-347, and SREV-348. |
| Schema | `GUI_DDE_SERVICE_PROXY_TOPOLOGY_COMMENT` says `DdeProxyThreadSlave` owns the SbieSvc service-side DDE proxy window and transport edge; `guidde.c` owns sandbox-side DDE hook and posted-DDE reconstruction topology; private win32k and integrity-level observations are evidence, not API contract; legal shape remains documented DDE messages and DDE `lParam` helpers; `WM_COPYDATA` is a `SendMessage`-only copy boundary; SREV-084 owns ACK `lParam` forwarding; SREV-347 owns direct ACK startup; SREV-348 owns request/data route mapping; this SREV changes comments and proof only. |
| Topology | `SendPostMessageSlave direct WM_DDE_ACK startup -> DdeProxyThreadSlave -> _DDE_ProxyClass2 service proxy window -> SendMessage(real client, WM_DDE_ACK, proxy HWND, initial lParam)`. Then `proxy receives WM_DDE_EXECUTE / WM_DDE_REQUEST -> optional SREV-348 request route registration -> SendMessage(sandbox server, WM_COPYDATA, proxy HWND, copied DDE payload)`. Server replies return through SREV-084 ACK forwarding or SREV-348 DATA route mapping. |
| Logic Risk | If the service comment frames the proxy as an `IL bug` workaround, future edits may optimize around the wording instead of preserving the legal crossing: posted DDE payloads cross through a SbieSvc proxy window and copied `WM_COPYDATA` payloads. SREV-084 and SREV-348 show this boundary is protocol-shape sensitive. |
| Official Shape | Microsoft documents DDE as a window-message protocol; `WM_DDE_EXECUTE` posts command data; `WM_DDE_REQUEST` requests a data item; `WM_DDE_ACK` reports DDE processing; `PackDDElParam` / `UnpackDDElParam` own posted DDE `lParam` shape; and `WM_COPYDATA` data is valid only while the receiving application processes the `SendMessage`. |
| Fix | Comment-only source clarification. The source now names SREV-351, calls `DdeProxyThreadSlave` the out-of-sandbox transport endpoint, names the restricted-token posted-DDE topology, and explains why the proxy uses `WM_COPYDATA` as a copy boundary. No DDE ACK forwarding, request route map, proxy window class, timer, message loop, `WM_COPYDATA` packing, or DDE message posting behavior changed. |
| Acceptance Gate | `docs/plan/check-srev-351.py` validates the draft-07 schema, official references, service-side topology comment, stale `IL bug` wording removal from the service comment, SREV-084 / SREV-293 / SREV-347 / SREV-348 adjacency, combined ledger entry, and split ledger fragment; `docs/plan/check-srev-351.sh` is the targeted wrapper. Runtime gate: none for this comment-only clarification. The inherited Windows DDE runtime gates remain SREV-084 ACK forwarding proof, SREV-347 direct ACK startup proof, and SREV-348 overlapping request/data route proof. |
