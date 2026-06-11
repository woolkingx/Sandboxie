# SREV-084: DDE Proxy ACK lParam Forwarding

## Data

`Sandboxie/core/dll/guidde.c` and `Sandboxie/core/svc/GuiServer.cpp` implement
a DDE proxy path for conversations that cross the sandbox boundary.

The relevant data nodes are:

```text
client DDE window
proxy DDE window
sandbox server DDE window
posted WM_DDE_EXECUTE / WM_DDE_REQUEST
server posted WM_DDE_ACK
packed DDE ACK lParam
proxy-forwarded WM_DDE_ACK
```

## Official Shape

Microsoft documents DDE as a message protocol between windows. `WM_DDE_INITIATE`
and the ACK sent in response to it use `SendMessage`; other DDE messages are
posted.

Microsoft documents `WM_DDE_EXECUTE` as carrying a global memory object in
`lParam`, and documents that the server is expected to post a `WM_DDE_ACK` in
response.

Microsoft documents `WM_DDE_ACK` as having message-specific `wParam` and
`lParam` shape. When responding to `WM_DDE_EXECUTE`, `lParam` contains the ACK
flags in the low-order part and the global memory object handle in the
high-order part. Posted DDE ACK `lParam` values must be created or reused with
the DDE lParam helper functions and the receiver frees the posted `lParam`.

Microsoft documents `PackDDElParam` as creating the `lParam` value for a posted
DDE message, and `UnpackDDElParam` as unpacking the `lParam` from a posted DDE
message.

Microsoft documents `WM_COPYDATA` data as valid only while the message is being
processed; receivers that need the data later must copy it.

```text
https://learn.microsoft.com/en-us/windows/win32/dataxchg/about-dynamic-data-exchange
https://learn.microsoft.com/en-us/windows/win32/dataxchg/wm-dde-ack
https://learn.microsoft.com/en-us/windows/win32/dataxchg/wm-dde-execute
https://learn.microsoft.com/en-us/windows/win32/api/dde/nf-dde-packddelparam
https://learn.microsoft.com/en-us/windows/win32/api/dde/nf-dde-unpackddelparam
https://learn.microsoft.com/en-us/windows/win32/dataxchg/wm-copydata
```

## Schema

Local schema:

```text
docs/plan/srev-084-dde-proxy-ack-lparam.schema.json
```

The ACK forwarding contract is:

```text
the DDE proxy is a transport boundary, not the owner of ACK semantics
a received server WM_DDE_ACK carries its own official lParam shape
the proxy forwards the received ACK lParam unchanged to the real client
the proxy must not reuse the previous client EXECUTE/REQUEST lParam as ACK lParam
WM_COPYDATA bridge payloads are copied before later DDE posting
```

## Topology

```text
external client posts WM_DDE_EXECUTE / WM_DDE_REQUEST
  -> SbieSvc DDE proxy window
  -> WM_COPYDATA copy into sandbox server
  -> sandbox server posts WM_DDE_ACK
  -> SbieSvc DDE proxy window
  -> external client receives WM_DDE_ACK with server ACK lParam
```

`GuiServer::DdeProxyThreadSlave` owns only the proxy transport edge. The server
window owns the ACK response shape, and the proxy must preserve it when
forwarding to the client.

## Logic Risk

Before this patch, the proxy forwarded `WM_DDE_ACK` to the real client using
the thread-local `lParam` variable. That variable is reused for earlier DDE
messages in the same proxy loop, including the original client
`WM_DDE_EXECUTE` / `WM_DDE_REQUEST`. As a result, the final ACK could carry a
stale prior DDE `lParam` instead of the `msg.lParam` received with the server
ACK.

That violates the official DDE message shape: ACK is not a generic completion
signal; its `lParam` is part of the ACK payload and carries DDEACK/global-memory
state for the specific reply.

## Fix

`GuiServer::DdeProxyThreadSlave` now forwards `msg.lParam` when relaying a
server `WM_DDE_ACK` to the real client. This keeps the proxy at the transport
boundary and preserves the server-owned ACK payload.

## Acceptance Gate

`docs/plan/check-srev-084.py` validates the draft-07 schema, official
references, DDE proxy source evidence, received-ACK `msg.lParam` forwarding,
stale local `lParam` forwarding removal, and ledger entry.

Windows gate: an external DDE client talking to a sandboxed DDE server through
the proxy receives `WM_DDE_ACK` with the server's packed ACK `lParam`, including
`WM_DDE_EXECUTE` and `WM_DDE_REQUEST` response paths. Source-level gates do not
prove this runtime path.
