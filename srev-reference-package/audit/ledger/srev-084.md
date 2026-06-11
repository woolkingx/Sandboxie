---
kind: srev-ledger-entry
id: SREV-084
title: DDE Proxy ACK lParam Forwarding
status: patched-source-level-after-official-dde-wm-dde-ack-posted-dde-lparam-shape-and-l
owner: Sandboxie/core/dll/guidde.c
spec: docs/plan/srev-084-dde-proxy-ack-lparam.md
schema: docs/plan/srev-084-dde-proxy-ack-lparam.schema.json
checker: docs/plan/check-srev-084.py
runtime_gate: "an external DDE client talking to a sandboxed DDE server through the proxy receives `WM_DDE_ACK` with the server's packed ACK `lParam`, including `WM_DDE_EXECUTE` and `WM_DDE_REQUEST` response paths"
---
### SREV-084: DDE Proxy ACK lParam Forwarding

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official DDE `WM_DDE_ACK` / posted DDE lParam shape and local proxy topology analysis; needs Windows DDE proxy runtime proof |
| Evidence | `Sandboxie/core/dll/guidde.c` documents a DDE proxy workaround for restricted-token / integrity-level DDE message delivery and uses DDE lParam helpers around posted DDE data. Microsoft documents DDE as a window-message protocol, `WM_DDE_EXECUTE` as carrying a global memory object in `lParam`, `WM_DDE_ACK` as carrying response-specific payload in `lParam`, and `PackDDElParam` / `UnpackDDElParam` as the official posted-DDE lParam shape. Before this patch, `Sandboxie/core/svc/GuiServer.cpp` `DdeProxyThreadSlave` forwarded a server `WM_DDE_ACK` to the real client using the proxy thread's local `lParam` variable, which can hold a previous client `WM_DDE_EXECUTE` / `WM_DDE_REQUEST` value rather than the received server ACK payload. |
| Data | External client DDE window, SbieSvc proxy DDE window, sandbox server DDE window, posted `WM_DDE_EXECUTE` / `WM_DDE_REQUEST`, received server `WM_DDE_ACK`, packed ACK `lParam`, and proxy-forwarded ACK. |
| Schema | `DDE_PROXY_ACK_LPARAM_FORWARDING` says the DDE proxy is a transport boundary rather than the owner of ACK semantics; a received server `WM_DDE_ACK` carries its own official `lParam` shape; the proxy forwards the received ACK `lParam` unchanged to the real client; the proxy must not reuse the previous client `EXECUTE` / `REQUEST` `lParam` as ACK `lParam`; `WM_COPYDATA` bridge payloads are copied before later DDE posting. |
| Topology | External client DDE messages cross into the SbieSvc DDE proxy window, then into the sandbox server through copied `WM_COPYDATA` payloads. The sandbox server posts `WM_DDE_ACK` back through the proxy. `DdeProxyThreadSlave` owns only the transport edge and must preserve the server-owned ACK payload when posting the final ACK to the client. |
| Logic Risk | DDE ACK is not a generic boolean completion signal. Its `lParam` is the reply payload and carries DDEACK/global-memory state for the corresponding DDE message. Reusing a stale proxy-loop variable can corrupt the protocol shape seen by the real client, especially after `WM_DDE_EXECUTE` or `WM_DDE_REQUEST`. |
| Official Shape | `docs/plan/srev-084-dde-proxy-ack-lparam.md` records Microsoft DDE protocol, `WM_DDE_ACK`, `WM_DDE_EXECUTE`, `PackDDElParam`, `UnpackDDElParam`, and `WM_COPYDATA` references. `docs/plan/srev-084-dde-proxy-ack-lparam.schema.json` records the JSON Schema draft-07 local `DDE_PROXY_ACK_LPARAM_FORWARDING` contract. |
| Fix | `GuiServer::DdeProxyThreadSlave` now forwards `msg.lParam` when relaying a server `WM_DDE_ACK` to the real client, preserving the received ACK payload instead of using the thread's stale local `lParam` variable. |
| Acceptance Gate | `docs/plan/check-srev-084.py` validates the draft-07 schema, official references, DDE proxy source evidence, received-ACK `msg.lParam` forwarding, stale local `lParam` forwarding removal, and ledger entry; `docs/plan/check-srev-084.sh` is the matrix wrapper. Windows gate: an external DDE client talking to a sandboxed DDE server through the proxy receives `WM_DDE_ACK` with the server's packed ACK `lParam`, including `WM_DDE_EXECUTE` and `WM_DDE_REQUEST` response paths. |
