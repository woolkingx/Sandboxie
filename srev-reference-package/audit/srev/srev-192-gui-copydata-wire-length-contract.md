# SREV-192 GUI COPYDATA Wire Length Contract

| Field | Content |
|---|---|
| Stage | schema -> boundary -> action -> verify |
| Input Artifact | `Sandboxie/core/svc/GuiWire.h`, `Sandboxie/core/svc/GuiServer.cpp`, `Sandboxie/core/dll/guimsg.c`, and `Sandboxie/core/dll/guidde.c`. |
| Output Artifact | Draft-07 schema, source checker, split ledger fragment, and source readback proving the GUI `WM_COPYDATA` proxy uses a byte-tail wire contract and validates the fixed header before reading `cds_len`. |
| Owner | `Sandboxie/core/svc/GuiWire.h` owns the GUI proxy wire shape; `Sandboxie/core/svc/GuiServer.cpp` owns service-side request validation for `GUI_SEND_COPYDATA`. |
| Acceptance Gate | `docs/plan/check-srev-192.py`, `docs/plan/check-srev-192.sh`, core coverage, full SREV/KPATH matrix, and `git diff --check`. |

## Data

`GUI_SEND_COPYDATA_REQ` carries Sandboxie's local proxy form of a
`WM_COPYDATA` message. The payload node is `cds_len` bytes starting at
`cds_buf`.

Before this SREV:

- `GuiWire.h` declared the payload tail as `WCHAR cds_buf[1]`.
- `GuiServer::SendCopyDataSlave` checked `args->req_len < sizeof(GUI_SEND_COPYDATA)`.
- `GUI_SEND_COPYDATA` is the enum request id, not the request structure.
- The server then read `req->cds_len` and calculated the payload range.

That meant a malformed request shorter than the fixed header could pass the
first gate and make the server read `cds_len` from outside the supplied request
shape.

## Official API Shape

Microsoft documents `COPYDATASTRUCT` as:

```text
ULONG_PTR dwData
DWORD cbData
PVOID lpData
```

`cbData` is the size in bytes of the data pointed to by `lpData`, and `lpData`
is generic `PVOID` data. Microsoft's `WM_COPYDATA` page says `lParam` is a
pointer to a `COPYDATASTRUCT`; the referenced data is valid only during message
processing and must be copied if needed later.

Official references:

- `https://learn.microsoft.com/en-us/windows/win32/api/winuser/ns-winuser-copydatastruct`
- `https://learn.microsoft.com/en-us/windows/win32/dataxchg/wm-copydata`

## Boundary

The boundary is:

```text
sandboxed sender COPYDATASTRUCT
-> DLL GUI_SEND_COPYDATA_REQ byte-tail request
-> SbieSvc SendCopyDataSlave validation
-> host COPYDATASTRUCT
-> SendMessage / SendMessageTimeout / DDE bridge
```

At this boundary, `cds_len` is a byte count. The service must prove the fixed
header exists before reading `cds_len`, then prove the variable byte tail fits
inside `args->req_len` before creating the host `COPYDATASTRUCT`.

## Topology

The legal topology is:

```text
FIELD_OFFSET(GUI_SEND_COPYDATA_REQ, cds_buf)
-> fixed header minimum
-> cds_len <= 1 MiB compatibility cap
-> FIELD_OFFSET + cds_len within req_len
-> COPYDATASTRUCT.cbData = cds_len
-> COPYDATASTRUCT.lpData = cds_buf
```

The enum request id is not a structure owner and must never be used as a size
gate.

## Logic Risk

Using `sizeof(GUI_SEND_COPYDATA)` checks the enum constant width, not the wire
request header. A short or malformed request can therefore reach `req->cds_len`
without proving that the `cds_len` field exists. Declaring the payload tail as
`WCHAR` also misnames the API shape: `WM_COPYDATA` transports arbitrary bytes,
including DDE binary data, not necessarily text.

## Fix

- `GUI_SEND_COPYDATA_REQ::cds_buf` is now `UCHAR cds_buf[1]`.
- `SendCopyDataSlave` validates `FIELD_OFFSET(GUI_SEND_COPYDATA_REQ, cds_buf)`
  before reading payload-dependent state.
- The service tail range check uses the same fixed header offset plus
  `cds_len`.
- DLL request allocation in `guimsg.c` and `guidde.c` uses the fixed header
  offset plus byte length, matching the service gate.

No `WM_COPYDATA` allow/deny policy, integrity-level check, DDE routing, message
send API selection, or timeout behavior was otherwise changed.

## Runtime Gate

Linux source checks prove the local wire schema and length gates. A Windows gate
remains required: build SbieSvc and the DLL, send normal `WM_COPYDATA`, send DDE
copydata, and fault-inject short requests shorter than the fixed header and
tails shorter than `cds_len` to prove clean `STATUS_INFO_LENGTH_MISMATCH`.
