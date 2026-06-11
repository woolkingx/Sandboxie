---
kind: srev-ledger-entry
id: SREV-293
title: GuiDDE DDE Proxy Topology Comment
status: patched-comment-topology-after-official-dde-protocol-and-srev-084-review-no-behavior-change
owner: Sandboxie/core/dll/guidde.c
spec: docs/plan/srev-293-guidde-dde-proxy-topology-comment.md
schema: docs/plan/srev-293-guidde-dde-proxy-topology-comment.schema.json
checker: docs/plan/check-srev-293.py
runtime_gate: SREV-084 DDE proxy Windows proof plus external DDE client sandboxed server smoke for INITIATE EXECUTE REQUEST ACK and WM_COPYDATA bridge behavior
---

### SREV-293: GuiDDE DDE Proxy Topology Comment

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | patched comment/topology after official DDE protocol and SREV-084 review; no behavior change |
| Evidence | `guidde.c` opens with a DDE conversation topology note. It describes a restricted-token / UIPI interaction where posted DDE message retrieval can lose message and `lParam`, then explains the Sandboxie proxy flow through a sandbox dummy/proxy window and the SbieSvc GUI Proxy window. The old wording called the private win32k observation a bug and called the proxy design a workaround. |
| Data | `WM_DDE_INITIATE`, `WM_DDE_ACK`, `WM_DDE_EXECUTE`, `WM_DDE_REQUEST`, `WM_COPYDATA`, `Gui_DDE_INITIATE_Received`, `Gui_DDE_ACK_Sending`, `Gui_DDE_COPYDATA_Received`, `Gui_DDE_Post_In_Box`, `DdeProxyThreadSlave`, `PackDDElParam`, `UnpackDDElParam`, SREV-084, and private win32k observation names. |
| Schema | `GUIDDE_DDE_PROXY_TOPOLOGY_COMMENT` says `guidde.c` owns local DDE hook and proxy translation logic; SbieSvc GUI Proxy owns the out-of-process DDE proxy window and transport edge; private win32k call-stack names are observation evidence, not API contract; the legal protocol shape remains documented DDE messages and payload helpers; SREV-084 owns DDE ACK `lParam` forwarding behavior; this SREV changes comments and proof only. |
| Topology | `WM_DDE_INITIATE received in sandbox -> Gui_DDE_INITIATE_Received replaces out-of-box client HWND with proxy HWND -> TLS records real client/proxy edge`; `WM_DDE_ACK sending path -> Gui_DDE_ACK_Sending restores the real client HWND when appropriate`; `SbieSvc GUI Proxy -> DdeProxyThreadSlave owns the external transport window -> SREV-084 requires received server ACK lParam forwarding`; `WM_COPYDATA bridge -> Gui_DDE_COPYDATA_Received converts copied proxy payloads back to posted DDE messages`. |
| Logic Risk | If the comment frames this as only a win32k bug workaround, future changes may optimize against private call-stack names instead of preserving the documented DDE payload shape and local owner split. SREV-084 already found a concrete protocol-shape bug in ACK `lParam` forwarding. |
| Official Shape | Microsoft documents DDE as a window-message protocol. `WM_DDE_INITIATE` and the corresponding ACK are sent messages; other DDE messages are posted. Microsoft documents `WM_DDE_ACK`, `WM_DDE_EXECUTE`, `PackDDElParam`, `UnpackDDElParam`, and `WM_COPYDATA` as the relevant message and payload shapes already captured by SREV-084. |
| Fix | Comment-only source clarification. The source now names SREV-293, describes the private win32k path as observed behavior rather than an API contract, and names the dummy/SbieSvc windows as compatibility topology. No DDE hook installation, TLS storage, proxy lookup, `WM_COPYDATA` bridge, posted message conversion, or SbieSvc proxy behavior changed. |
| Acceptance Gate | `docs/plan/check-srev-293.py` validates the draft-07 schema, official references, source comment, stale bug/workaround wording removal, core DDE proxy flow functions, SREV-084 adjacency, combined ledger entry, and split ledger fragment; `docs/plan/check-srev-293.sh` is the targeted wrapper. Runtime gate: inherited DDE proxy Windows proof from SREV-084 plus an external DDE client / sandboxed server smoke that observes `WM_DDE_INITIATE`, `WM_DDE_EXECUTE`, `WM_DDE_REQUEST`, `WM_DDE_ACK`, and `WM_COPYDATA` bridge behavior across the SbieSvc proxy. |
