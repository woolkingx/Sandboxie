# SREV-293: GuiDDE DDE Proxy Topology Comment

## Stage Gate

| Field | Value |
|---|---|
| Stage | schema -> boundary -> topology -> verify |
| Input artifact | `Sandboxie/core/dll/guidde.c`, `Sandboxie/core/svc/GuiServer.cpp`, SREV-084, Microsoft DDE references |
| Output artifact | Source comment owner, draft-07 schema, targeted checker, ledger fragment |
| Owner | `guidde.c` DDE conversation topology comment |
| Acceptance gate | Targeted checker validates source comment, DDE proxy flow adjacency, SREV-084 adjacency, stale bug/workaround wording removal, and ledger fragment |

## Data

`guidde.c` opens with a DDE conversation topology note. It describes a
restricted-token / UIPI interaction where posted DDE message retrieval can lose
the message number and `lParam`, then explains the Sandboxie proxy flow:

```text
external DDE client
  -> sandbox dummy/proxy window
  -> SbieSvc GUI Proxy DDE window
  -> sandbox server window
  -> WM_COPYDATA bridge
  -> posted WM_DDE_* messages
```

The old wording called the private win32k observation a bug and called the
proxy design a workaround. That wording is too loose for a protocol boundary:
the private win32k call chain is observation evidence, while the legal shape is
the documented DDE message protocol plus local proxy ownership.

## Official Shape

Microsoft documents DDE as a window-message protocol. `WM_DDE_INITIATE` and
the corresponding ACK are sent messages; other DDE messages are posted.

Microsoft documents `WM_DDE_ACK`, `WM_DDE_EXECUTE`, `PackDDElParam`,
`UnpackDDElParam`, and `WM_COPYDATA` as the relevant message and payload
shapes already captured by SREV-084.

Official references:

- `https://learn.microsoft.com/en-us/windows/win32/dataxchg/about-dynamic-data-exchange`
- `https://learn.microsoft.com/en-us/windows/win32/dataxchg/wm-dde-ack`
- `https://learn.microsoft.com/en-us/windows/win32/dataxchg/wm-dde-execute`
- `https://learn.microsoft.com/en-us/windows/win32/api/dde/nf-dde-packddelparam`
- `https://learn.microsoft.com/en-us/windows/win32/api/dde/nf-dde-unpackddelparam`
- `https://learn.microsoft.com/en-us/windows/win32/dataxchg/wm-copydata`

## Schema

Local schema:

```text
docs/plan/srev-293-guidde-dde-proxy-topology-comment.schema.json
```

Contract id:

```text
GUIDDE_DDE_PROXY_TOPOLOGY_COMMENT
```

## Boundary

```text
user32 DDE messages
  -> Sandboxie DLL hooks in guidde.c / guimsg.c / gui.c
  -> SbieSvc GUI Proxy transport
  -> sandbox server window
```

`guidde.c` owns the local DDE hook/proxy translation logic. SbieSvc owns the
out-of-process proxy window and transport edge. Windows owns the private win32k
implementation details; the source comment must not treat those private names
as a stable API contract.

## Topology

```text
WM_DDE_INITIATE received in sandbox
  -> Gui_DDE_INITIATE_Received replaces out-of-box client HWND with proxy HWND
  -> TLS records real client/proxy edge

WM_DDE_ACK sending path
  -> Gui_DDE_ACK_Sending restores the real client HWND when appropriate

SbieSvc GUI Proxy
  -> DdeProxyThreadSlave owns the external transport window
  -> SREV-084 requires received server ACK lParam forwarding

WM_COPYDATA bridge
  -> Gui_DDE_COPYDATA_Received converts copied proxy payloads back to posted DDE messages
```

## Logic Risk

If the comment frames this as only a win32k bug workaround, future changes may
optimize against private call-stack names instead of preserving the documented
DDE payload shape and local owner split. That is especially risky because
SREV-084 already found a concrete protocol-shape bug in ACK `lParam`
forwarding.

## Fix

Comment-only source clarification. The source now names SREV-293, describes the
private win32k path as observed behavior rather than an API contract, and names
the dummy/SbieSvc windows as compatibility topology. No DDE hook installation,
TLS storage, proxy lookup, `WM_COPYDATA` bridge, posted message conversion, or
SbieSvc proxy behavior changed.

## Acceptance Gate

`docs/plan/check-srev-293.py` validates the draft-07 schema, official
references, source comment, stale bug/workaround wording removal, core DDE
proxy flow functions, SREV-084 adjacency, combined ledger entry, and split
ledger fragment.

Runtime gate: inherited DDE proxy Windows proof from SREV-084 plus an external
DDE client / sandboxed server smoke that observes `WM_DDE_INITIATE`,
`WM_DDE_EXECUTE`, `WM_DDE_REQUEST`, `WM_DDE_ACK`, and `WM_COPYDATA` bridge
behavior across the SbieSvc proxy.
