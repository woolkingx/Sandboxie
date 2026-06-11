# SREV-348: GUI DDE DATA Proxy Route Map

| Field | Content |
|---|---|
| Stage | schema -> boundary -> topology -> action -> verify |
| Input artifact | `Sandboxie/core/svc/GuiServer.cpp`, `Sandboxie/core/dll/guidde.c`, `Sandboxie/core/dll/guimsg.c`, `Sandboxie/core/svc/GuiWire.h`, SREV-084, SREV-192, SREV-293, SREV-347, and Microsoft DDE / message-queue documentation |
| Output artifact | Source patch, draft-07 schema, checker, and ledger fragment |
| Owner | `GuiServer::DdeProxyThreadSlave` and `GuiServer::SendCopyDataSlave` DDE request/data return edge |
| Acceptance gate | Targeted checker validates official references, per-request route map shape, `WM_DDE_REQUEST` item extraction, `WM_DDE_DATA` reply lookup, stale single global proxy window removal, DDE proxy topology preservation, and ledger fragment |

## Data

`DdeProxyThreadSlave` owns the SbieSvc proxy window for one DDE conversation.
When the external client posts `WM_DDE_REQUEST`, the proxy converts the request
to `WM_COPYDATA` for the sandboxed server. When the sandboxed server later posts
`WM_DDE_DATA`, `Gui_DDE_DATA_Posting` copies the `DDEDATA` payload and calls
`GUI_SEND_COPYDATA` with `which='dde '`, `hwnd` set to the real client HWND, and
`cds_key` set to the high word extracted from the posted `WM_DDE_DATA` lParam.

Before this SREV, the service remembered the proxy window for the pending
request in one process-global `DDE_Request_ProxyWnd`. That comment already
called it a global variable hack. Multiple DDE proxy threads or overlapping
client requests could overwrite that single HWND before the matching
`WM_DDE_DATA` reply arrived.

## Official Shape

Microsoft documents DDE as a window-message protocol. A DDE server responds to
`WM_DDE_REQUEST` by posting `WM_DDE_DATA` to the client. `WM_DDE_DATA` carries a
global memory handle in the low-order word and an atom identifying the data item
in the high-order word. `WM_DDE_DATA` lParam values must be created or reused
through DDE lParam helpers. `PackDDElParam` and `UnpackDDElParam` are the
documented helpers for posted DDE message lParam packing and unpacking.

Microsoft documents `PostMessage` as posting to the queue associated with the
thread that created the specified window and returning without waiting for
processing. Therefore the SbieSvc private hop must post to the correct proxy
window for the specific pending DDE request, not to the last request observed
process-wide.

Official references:

- `https://learn.microsoft.com/en-us/windows/win32/dataxchg/about-dynamic-data-exchange`
- `https://learn.microsoft.com/en-us/windows/win32/dataxchg/wm-dde-request`
- `https://learn.microsoft.com/en-us/windows/win32/dataxchg/wm-dde-data`
- `https://learn.microsoft.com/en-us/windows/win32/api/dde/nf-dde-packddelparam`
- `https://learn.microsoft.com/en-us/windows/win32/api/dde/nf-dde-unpackddelparam`
- `https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-postmessagew`
- `https://learn.microsoft.com/en-us/windows/win32/winmsg/about-messages-and-message-queues`

## Boundary

The `WM_DDE_REQUEST` to `WM_DDE_DATA` return edge crosses three owners:

```text
SbieSvc proxy window
  -> sandboxed server receives WM_DDE_REQUEST
  -> sandboxed server posts WM_DDE_DATA
  -> SbieSvc posts private WM_USER hop to the owning proxy window
  -> proxy window posts WM_DDE_DATA to the real client
```

The route owner is the pending request, not the SbieSvc process. A single
process-global HWND cannot represent multiple live proxy windows.

## Topology

```text
DdeProxyThreadSlave receives WM_DDE_REQUEST
  -> UnpackDDElParam(WM_DDE_REQUEST) extracts DDE item atom
  -> Dde_SetRequestProxyWnd(real client HWND, item atom, SbieSvc proxy HWND)
  -> SendMessage(WM_COPYDATA) to sandbox server
  -> sandbox server posts WM_DDE_DATA
  -> Gui_DDE_DATA_Posting extracts WM_DDE_DATA item atom
  -> GUI_SEND_COPYDATA which='dde ', hwnd=real client HWND, cds_key=item atom
  -> SendCopyDataSlave Dde_TakeRequestProxyWnd(real client HWND, item atom)
  -> private PostMessage to the matched SbieSvc proxy window
  -> DdeProxyThreadSlave posts WM_DDE_DATA to the real client
```

Rejected route:

```text
last DDE request in process -> global proxy HWND -> unrelated WM_DDE_DATA reply
```

## Logic Risk

The previous single global route was a topology bug. If two DDE conversations
or two item requests overlapped, the second request could overwrite the proxy
HWND needed by the first response. The first `WM_DDE_DATA` could then be posted
to the wrong proxy thread or fail after the global was cleared by another
thread.

The legal routing key already exists in the local protocol: `Gui_DDE_DATA_Posting`
sends the real client HWND in `GUI_SEND_COPYDATA_REQ.hwnd` and the DDE item atom
in `cds_key`. `DdeProxyThreadSlave` can extract the same item atom from the
corresponding `WM_DDE_REQUEST` lParam.

## Fix

`GuiServer.cpp` now stores pending DDE request routes in a small service-local
map keyed by real client HWND and DDE item atom. `DdeProxyThreadSlave` records
the route after unpacking `WM_DDE_REQUEST`; `SendCopyDataSlave` takes and
removes the matching route before posting the private `WM_USER + 0x123` hop to
the owning proxy window.

The source keeps the existing DDE payload copy, `WM_COPYDATA` bridge,
`WM_DDE_DATA` packing, private proxy-thread hop, and final client `PostMessage`
topology. This is source-level hardening; Windows DDE runtime proof is still
required.

## Acceptance Gate

`docs/plan/check-srev-348.py` validates the draft-07 schema, official
references, local `WM_DDE_REQUEST` / `WM_DDE_DATA` item atom shape, the
service-local route map, route set/take locking, stale single-HWND global
removal, `SendCopyDataSlave` lookup by real client HWND plus `cds_key`,
`DdeProxyThreadSlave` route registration by unpacked item atom, combined ledger
entry, and split ledger fragment.

Runtime gate: Windows SbieSvc/DLL build plus DDE request/data smoke with two
overlapping external-client to sandbox-server DDE item requests proving each
`WM_DDE_DATA` returns through its own SbieSvc proxy window and stale/missing
route returns failure without posting to an unrelated proxy.
