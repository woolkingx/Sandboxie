# SREV-351: GUI DDE Service Proxy Topology Comment

| Field | Content |
|---|---|
| Stage | schema -> boundary -> topology -> verify |
| Input artifact | `Sandboxie/core/svc/GuiServer.cpp`, SREV-084, SREV-293, SREV-347, SREV-348, and Microsoft DDE / `WM_COPYDATA` documentation |
| Output artifact | Comment-only source patch, draft-07 schema, targeted checker, and ledger fragment |
| Owner | `GuiServer::DdeProxyThreadSlave` service-side DDE proxy topology comment |
| Acceptance gate | Targeted checker validates official references, service proxy topology comment, stale `IL bug` wording removal, DDE ACK / REQUEST / DATA adjacency, SREV-084 / SREV-293 / SREV-347 / SREV-348 adjacency, and ledger fragment |

## Data

`DdeProxyThreadSlave` creates the SbieSvc-side proxy window used by the DDE
bridge. To the external DDE client, the proxy window behaves as the DDE server.
To the sandboxed server, it behaves as the client.

The function participates in three already-reviewed DDE edges:

```text
initial WM_DDE_ACK
  -> SREV-347 validates direct SendMessage startup and client HWND validity
  -> SREV-084 preserves received server ACK lParam forwarding

posted WM_DDE_EXECUTE / WM_DDE_REQUEST
  -> SbieSvc proxy receives posted DDE payloads
  -> sandbox server receives copied payloads through WM_COPYDATA

WM_DDE_REQUEST / WM_DDE_DATA reply routing
  -> SREV-348 records request routes by real client HWND and item atom
  -> matching WM_DDE_DATA returns through the owning proxy window
```

Before this SREV, the local service comment described the need for the proxy as
an `IL bug in core/dll/guidde.c`. That phrase is too loose for a protocol
boundary. SREV-293 already reframed the `guidde.c` side as a restricted-token /
UIPI posted-DDE compatibility topology, with private win32k observations treated
as evidence rather than as the API contract.

## Official Shape

Microsoft documents DDE as a window-message protocol. A client posts
`WM_DDE_EXECUTE` to send command data and posts `WM_DDE_REQUEST` to request a
data item. Posted DDE message payloads are represented by the documented DDE
`lParam` helpers such as `PackDDElParam` and `UnpackDDElParam`.

Microsoft documents `WM_COPYDATA` as a `SendMessage`-only data transfer where
the receiving application must treat the data as valid only during processing
of the message. Therefore the service proxy is a transport/copy boundary; it is
not the owner of DDE payload semantics.

Official references:

- `https://learn.microsoft.com/en-us/windows/win32/dataxchg/about-dynamic-data-exchange`
- `https://learn.microsoft.com/en-us/windows/win32/dataxchg/wm-dde-execute`
- `https://learn.microsoft.com/en-us/windows/desktop/dataxchg/wm-dde-request`
- `https://learn.microsoft.com/en-us/windows/win32/dataxchg/wm-dde-ack`
- `https://learn.microsoft.com/en-us/windows/win32/dataxchg/wm-copydata`
- `https://learn.microsoft.com/en-us/windows/win32/api/dde/nf-dde-packddelparam`
- `https://learn.microsoft.com/en-us/windows/win32/api/dde/nf-dde-unpackddelparam`

## Schema

Local schema:

```text
docs/plan/srev-351-gui-dde-service-proxy-topology-comment.schema.json
```

Contract id:

```text
GUI_DDE_SERVICE_PROXY_TOPOLOGY_COMMENT
```

## Boundary

```text
external DDE client
  -> SbieSvc proxy window owned by DdeProxyThreadSlave
  -> WM_COPYDATA transport into the sandbox server
  -> sandbox DLL posted-DDE reconstruction
```

`DdeProxyThreadSlave` owns the service-side proxy window and transport edge.
`guidde.c` owns the sandbox-side hook and posted-DDE reconstruction. Windows owns
the DDE protocol and the private window-manager implementation details.

## Topology

```text
SendPostMessageSlave direct WM_DDE_ACK startup
  -> DdeProxyThreadSlave
  -> RegisterClass("_DDE_ProxyClass2")
  -> CreateWindowEx proxy HWND
  -> SendMessage(real client, WM_DDE_ACK, proxy HWND, initial lParam)

proxy receives WM_DDE_EXECUTE / WM_DDE_REQUEST
  -> optional SREV-348 request route registration
  -> SendMessage(sandbox server, WM_COPYDATA, proxy HWND, copied DDE payload)

sandbox server response
  -> WM_DDE_ACK forwarding preserves msg.lParam by SREV-084
  -> WM_DDE_DATA routing uses SREV-348 route map
```

## Logic Risk

If the service comment frames the proxy as an `IL bug` workaround, future edits
may optimize around the wording instead of preserving the legal crossing:
posted DDE payloads cross through a SbieSvc proxy window and copied
`WM_COPYDATA` payloads. That is exactly where SREV-084 and SREV-348 found
protocol-shape-sensitive behavior.

## Fix

Comment-only source clarification. The source now names SREV-351, calls
`DdeProxyThreadSlave` the out-of-sandbox transport endpoint, names the
restricted-token posted-DDE topology, and explains why the proxy uses
`WM_COPYDATA` as a copy boundary. No DDE ACK forwarding, request route map,
proxy window class, timer, message loop, `WM_COPYDATA` packing, or DDE message
posting behavior changed.

## Acceptance Gate

`docs/plan/check-srev-351.py` validates the draft-07 schema, official
references, service-side topology comment, stale `IL bug` wording removal from
the service comment, SREV-084 / SREV-293 / SREV-347 / SREV-348 adjacency,
combined ledger entry, and split ledger fragment.

Runtime gate: none for this comment-only clarification. The inherited Windows
DDE runtime gates remain SREV-084 ACK forwarding proof, SREV-347 direct ACK
startup proof, and SREV-348 overlapping request/data route proof.
