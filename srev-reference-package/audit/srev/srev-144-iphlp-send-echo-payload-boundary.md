# SREV-144: IP Helper SendEcho Payload Boundary

## Stage Gate

| Field | Value |
|---|---|
| Stage | action |
| Input artifact | `Sandboxie/core/svc/iphlpserver.cpp`, `Sandboxie/core/svc/iphlpwire.h`, `Sandboxie/core/dll/iphlp.c`, Microsoft `IcmpSendEcho2`, `IcmpSendEcho2Ex`, `Icmp6SendEcho2`, and `IcmpCreateFile` references |
| Output artifact | `docs/plan/srev-144-iphlp-send-echo-payload-boundary.schema.json`, `docs/plan/check-srev-144.py`, `docs/plan/check-srev-144.sh`, ledger fragment |
| Owner | SbieSvc IP Helper ICMP echo proxy request-payload validation |
| Acceptance gate | source checker plus full SREV/KPATH/core coverage matrix; Windows runtime proof remains required for ICMP proxy paths |

## Evidence

`Sandboxie/core/svc/iphlpserver.cpp` was the top unnamed reviewable core file
after SREV-143. It registers the `MSGID_IPHLP` pipe target, creates proxy ICMP
handles with `IcmpCreateFile` / `Icmp6CreateFile`, and services
`MSGID_IPHLP_SEND_ECHO` by passing caller-supplied request bytes into
`IcmpSendEcho2`, `IcmpSendEcho2Ex`, or `Icmp6SendEcho2`.

The wire packet is declared in `Sandboxie/core/svc/iphlpwire.h` as
`IPHLP_SEND_ECHO_REQ`, with a counted flexible payload:

```text
ULONG request_size;
UCHAR request_data[1];
```

The normal DLL client in `Sandboxie/core/dll/iphlp.c` allocates
`sizeof(IPHLP_SEND_ECHO_REQ) + RequestSize`, sets `req->h.length`, and copies
`RequestData` into `request_data`. The service boundary cannot rely on that
client being the only possible sender. Before this SREV, `SendEchoHandler`
checked the minimum fixed packet size and upper bounds for `request_size` and
`reply_size`, but it did not check that `request_data + request_size` was inside
`req->h.length` before passing `req->request_data` to the Microsoft ICMP APIs.

Official references:

- https://learn.microsoft.com/en-us/windows/win32/api/icmpapi/nf-icmpapi-icmpsendecho2
- https://learn.microsoft.com/en-us/windows/win32/api/icmpapi/nf-icmpapi-icmpsendecho2ex
- https://learn.microsoft.com/en-us/windows/win32/api/icmpapi/nf-icmpapi-icmp6sendecho2
- https://learn.microsoft.com/en-us/windows/win32/api/icmpapi/nf-icmpapi-icmpcreatefile

## Data

`MSGID_IPHLP`, `MSGID_IPHLP_SEND_ECHO`, `IPHLP_SEND_ECHO_REQ`,
`IPHLP_SEND_ECHO_RPL`, `req->h.length`, `req->request_size`,
`req->request_data`, `req->reply_size`, `FIELD_OFFSET`, `IpHlp_CommonSend`,
`SbieDll_CallServer`, `IpHlpServer::Handler`, `IpHlpServer::SendEchoHandler`,
`ProxyHandle`, `PROXY_ICMP_HANDLE`, `m_IcmpSendEcho2`, `m_IcmpSendEcho2Ex`,
`m_Icmp6SendEcho2`, `IcmpSendEcho2`, `IcmpSendEcho2Ex`, and `Icmp6SendEcho2`.

## Schema

`IPHLP_SEND_ECHO_PAYLOAD_BOUNDARY` says:

- `iphlpserver.cpp` owns service-side validation of the IP Helper ICMP echo
  pipe request before any Microsoft ICMP API receives caller-supplied bytes.
- `IPHLP_SEND_ECHO_REQ.request_data` is a counted variable payload owned by
  `request_size`, not by the fixed struct size alone.
- The service accepts a SendEcho request only when `req->h.length` is at least
  the fixed request size, `request_size <= 0xFFFF`, `reply_size <= 0x0FFFFF`,
  and `FIELD_OFFSET(IPHLP_SEND_ECHO_REQ, request_data) + request_size <=
  req->h.length`.
- `RequestSize` passed to `IcmpSendEcho2`, `IcmpSendEcho2Ex`, and
  `Icmp6SendEcho2` remains a `WORD` derived from the already-bounded
  `request_size`.
- `reply_size` allocation and WOW64 reply widening stay unchanged.
- Proxy handle lookup, IP version matching, network access policy, and
  restricted-token ICMP handle creation stay unchanged.

## Topology

Legal SendEcho flow:

```text
DLL IpHlp_CommonSend
  -> build IPHLP_SEND_ECHO_REQ with request_size and request_data bytes
  -> SbieDll_CallServer(MSGID_IPHLP_SEND_ECHO)
  -> SbieSvc IpHlpServer::SendEchoHandler
  -> validate fixed header and counted request_data range inside h.length
  -> lookup per-process PROXY_ICMP_HANDLE
  -> select IcmpSendEcho2 / IcmpSendEcho2Ex / Icmp6SendEcho2
  -> pass req->request_data plus WORD RequestSize to the selected API
  -> copy/normalize reply data into IPHLP_SEND_ECHO_RPL
```

## Logic Risk

The service receives a variable-length packet from a pipe boundary. If the
fixed header is present but `request_size` points past the received packet, the
service can read beyond the message buffer and pass unrelated process memory as
ICMP request data. The Microsoft ICMP APIs define `RequestData` as a pointer to
a buffer and `RequestSize` as the byte size of that buffer; therefore the
service must prove the counted payload exists before the call.

This SREV does not change which ICMP API is used, how proxy handles are scoped,
how network policy is checked, how reply buffers are allocated, or how WOW64
reply structures are converted.

## Fix

`IpHlpServer::SendEchoHandler` now computes
`FIELD_OFFSET(IPHLP_SEND_ECHO_REQ, request_data)` and rejects the request when
`offset + req->request_size > req->h.length`. Existing `request_size` and
`reply_size` upper bounds remain unchanged.

## Acceptance Gate

`docs/plan/check-srev-144.py` validates the draft-07 schema, official reference
links, wire packet shape, DLL client packet construction, service-side counted
payload validation before proxy handle lookup and ICMP API calls, preservation
of `WORD RequestSize`, selected ICMP API routing, reply-size/WOW64 handling,
and the ledger fragment. `docs/plan/check-srev-144.sh` is the matrix wrapper.

Runtime/build gate: Windows service build; IPv4 `IcmpSendEcho2`,
`IcmpSendEcho2Ex`, and IPv6 `Icmp6SendEcho2` smoke through Sandboxie; malformed
SendEcho pipe packet with `request_size` larger than received `h.length`
returns `ERROR_INVALID_PARAMETER` without reading past the message; normal
zero-length and nonzero request-data pings still return valid reply status;
WOW64 minimal reply buffer conversion remains intact.
