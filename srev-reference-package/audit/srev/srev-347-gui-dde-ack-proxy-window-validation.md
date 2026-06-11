# SREV-347: GUI DDE ACK Proxy Window Validation

| Field | Content |
|---|---|
| Stage | schema -> boundary -> topology -> action -> verify |
| Input artifact | `Sandboxie/core/svc/GuiServer.cpp`, `Sandboxie/core/dll/guimsg.c`, `Sandboxie/core/dll/guidde.c`, `Sandboxie/core/svc/GuiWire.h`, SREV-084, SREV-293, and Microsoft DDE / window-message documentation |
| Output artifact | Source patch, draft-07 schema, checker, and ledger fragment |
| Owner | `GuiServer::SendPostMessageSlave` DDE ACK proxy startup path |
| Acceptance gate | Targeted checker validates official references, direct `SendMessageA/W` routing, `IsWindow` before proxy thread creation, timeout path non-proxy behavior, DDE proxy topology preservation, stale branch-shape removal, and ledger fragment |

## Data

`Gui_SendMessageA` and `Gui_SendMessageW` call `Gui_DDE_ACK_Sending` for
`WM_DDE_ACK`, then send a `GUI_SEND_POST_MESSAGE` request with `which` set to
`'sm a'` or `'sm w'`. `Gui_SendMessageTimeoutA/W` use `which` values
`'smta'` and `'smtw'` and do not call `Gui_DDE_ACK_Sending`.

`GuiServer::SendPostMessageSlave` starts `DdeProxyThreadSlave` when it sees a
direct `SendMessageA/W` `WM_DDE_ACK`. The proxy thread receives the client
window, server window, and initial ACK `lParam`, creates the SbieSvc DDE proxy
window, sends the initial `WM_DDE_ACK` to the real client, and then forwards
posted DDE traffic between client and server. SREV-084 owns ACK `lParam`
forwarding inside the proxy thread. SREV-293 owns the `guidde.c` topology
comment.

Before this SREV, the DDE ACK proxy branch also named timeout `which` values in
the outer condition, although the inner branch only proxied direct
`SendMessageA/W`. More importantly, C operator precedence meant the
`IsWindow(hwnd)` guard applied to `'sm a'` but not to `'sm w'`.

## Official Shape

Microsoft documents DDE as a message protocol between client and server
windows. A DDE conversation is identified by the pair of participating window
handles. Microsoft also documents that DDE `WM_DDE_ACK` in response to
`WM_DDE_INITIATE` is sent with `SendMessage`, while the other DDE messages are
posted.

`SendMessage` sends a message to a window procedure and does not return until
the window procedure has processed the message. `SendMessageTimeout` is a
separate API with timeout and abort flags. `IsWindow` checks whether a window
handle identifies an existing window, but its result is only a point-in-time
validation.

Official references:

- `https://learn.microsoft.com/en-us/windows/win32/dataxchg/about-dynamic-data-exchange`
- `https://learn.microsoft.com/en-us/windows/win32/dataxchg/wm-dde-ack`
- `https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-sendmessagew`
- `https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-sendmessagetimeoutw`
- `https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-iswindow`

## Boundary

The DDE proxy startup path is not a generic message send path. It is a
compatibility bridge for direct `SendMessageA/W` `WM_DDE_ACK` that establishes
the SbieSvc proxy window as the transport endpoint for the DDE conversation.

`SendMessageTimeoutA/W` requests still cross the normal SbieSvc message broker
path. They should not start the DDE proxy unless the local DLL first maps the
call into the same DDE ACK conversation setup state as direct `SendMessageA/W`.

## Topology

```text
sandboxed DDE server
  -> Gui_SendMessageA/W(WM_DDE_ACK)
  -> Gui_DDE_ACK_Sending restores real client HWND when needed
  -> GUI_SEND_POST_MESSAGE which='sm a'/'sm w'
  -> GuiServer::SendPostMessageSlave
  -> IsWindow(client HWND)
  -> DdeProxyThreadSlave
  -> SbieSvc DDE proxy window
  -> initial SendMessage(client HWND, WM_DDE_ACK, proxy HWND, lParam)
  -> posted DDE EXECUTE / REQUEST / DATA / ACK bridge
```

Rejected startup shape:

```text
WM_DDE_ACK + which='sm w' + invalid client HWND
  -> create proxy thread
```

Non-proxy shape:

```text
WM_DDE_ACK + which='smtw'/'smta'
  -> normal SendMessageTimeout broker path
```

## Logic Risk

The original branch looked like it validated the target window before starting
the proxy thread, but it only did so for ANSI `SendMessageA`. Unicode
`SendMessageW` bypassed `IsWindow(hwnd)` and could allocate arguments and start
a proxy thread for a stale or invalid client window handle.

That is a boundary-shape bug rather than a DDE payload bug: the proxy thread is
the DDE conversation transport owner and should only be created for a valid
client window edge.

## Fix

`SendPostMessageSlave` now starts the DDE ACK proxy only for direct
`SendMessageA/W` requests and applies `IsWindow(hwnd)` before allocating proxy
arguments or creating `DdeProxyThreadSlave`.

No DDE `lParam` forwarding, `WM_COPYDATA` bridge, `DDE_Request_ProxyWnd`,
timeout send behavior, OpenWinClass access checks, or general
`SendMessageTimeoutA/W` broker behavior changed.

## Acceptance Gate

`docs/plan/check-srev-347.py` validates the draft-07 schema, official
references, local direct-send / timeout routing evidence, `IsWindow` ordering
before `HeapAlloc` and `CreateThread`, stale unparenthesized A/W branch removal,
timeout `which` removal from the DDE proxy startup condition, proxy topology
preservation, combined ledger entry, and split ledger fragment.

Runtime gate: Windows SbieSvc/DLL build plus DDE smoke proving external client
to sandboxed server DDE initiation still creates the proxy for direct
`SendMessageA/W`, invalid/stale client HWND does not create a useless proxy
thread, and `SendMessageTimeoutA/W` keeps its normal timeout broker behavior.
