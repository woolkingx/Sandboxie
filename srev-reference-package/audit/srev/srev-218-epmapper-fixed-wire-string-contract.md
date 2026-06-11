# SREV-218: EpMapper Fixed Wire String Contract

## Stage

data -> schema -> boundary -> topology -> logic -> action -> verify

## Evidence

`Sandboxie/core/svc/EpMapperWire.h` was the top unnamed reviewable core file
after SREV-217. It defines the local service wire contract for
`MSGID_EPMAPPER_GET_PORT_NAME`: request field
`WCHAR wszPortId[DYNAMIC_PORT_ID_CHARS]` and reply field
`WCHAR wszPortName[DYNAMIC_PORT_NAME_CHARS]`.

Before this fix, `Sandboxie/core/dll/rpcrt.c` copied the caller supplied port id
into the request with `wcscpy(req.wszPortId, wszPortId)`. The service then used
`req->wszPortId` directly as a null-terminated string for `_wcsicmp`,
configuration lookup, `std::wstring` composition, trace output, and the
`API_OPEN_DYNAMIC_PORT` driver call. A malformed or oversized local service
message could therefore make the service scan beyond the fixed request field,
and a long DLL-side config tag could overflow the fixed request field before it
reached the service.

The interface-id path also parsed `RpcBindingToStringBindingW` output by adding
`+ 9` to the returned string and then forcing `wstrPortName[23] = 0`. That
encoded one expected example string rather than the official RPC string-binding
shape.

## Data

`EPMAPPER_GET_PORT_NAME_REQ`, `EPMAPPER_GET_PORT_NAME_RPL`,
`DYNAMIC_PORT_ID_CHARS`, `DYNAMIC_PORT_NAME_CHARS`, `GetDynamicLpcPortName`,
`StoreLpcPortName`, `EpmapperGetPortNameHandler`, `RpcBindingToStringBindingW`,
`ncalrpc:[endpoint]`, `RpcPortBindingIfId`, `RpcPortBindingSvc`,
`RpcPortFilter`, `Open[Name]Endpoint`, and `API_OPEN_DYNAMIC_PORT`.

## Official Shape

Microsoft documents `wcscpy_s` as taking the destination size in wide
characters, requiring space for the terminating null, and leaving successful
results null-terminated. The old `wcscpy` request fill did not carry the
destination size through the fixed wire boundary.

Microsoft documents RPC string bindings as:

```text
ObjectUUID@ProtocolSequence:NetworkAddress[Endpoint,Option]
```

For `ncalrpc`, the endpoint is a string inside the bracketed endpoint field.
Microsoft's MIDL `ncalrpc` page also names it as the local IPC protocol family
and says the port string is transport-defined. Therefore the service must prove
the `ncalrpc:[...]` envelope before extracting the endpoint; it must not assume
byte offset 9 and a hard-coded endpoint length.

References:

- `https://learn.microsoft.com/en-us/cpp/c-runtime-library/reference/strcpy-s-wcscpy-s-mbscpy-s?view=msvc-170`
- `https://learn.microsoft.com/en-us/windows/win32/rpc/string-binding`
- `https://learn.microsoft.com/en-us/windows/win32/midl/ncalrpc`

## Schema

`EPMAPPER_FIXED_WIRE_STRING_CONTRACT` says:

- `EpMapperWire.h` owns the fixed service wire fields for
  `MSGID_EPMAPPER_GET_PORT_NAME`.
- `wszPortId` is a fixed `WCHAR[DYNAMIC_PORT_ID_CHARS]` wire string and must be
  non-empty and null-terminated inside the field before any string API consumes
  it.
- `wszPortName` is a fixed `WCHAR[DYNAMIC_PORT_NAME_CHARS]` wire string and
  must be null-terminated inside the field before it crosses back to the DLL.
- The DLL must bounded-copy port ids and cached port names before storing them
  in fixed `IPC_DYNAMIC_PORT` fields or sending them through the service wire.
- The service must copy `req->wszPortId` into a bounded local `portId` before
  policy lookup or driver calls.
- `RpcBindingToStringBindingW` output must be parsed as a validated
  `ncalrpc:[endpoint]` string binding before the endpoint is copied.
- The service must not use magic offsets or hard-coded example endpoint
  lengths as the endpoint parser.

## Topology

```text
DLL config / built-in port id
-> RpcRt_CopyFixedWString
-> EPMAPPER_GET_PORT_NAME_REQ.wszPortId
-> SbieSvc PipeServer message
-> EpMapper_CopyFixedWString
-> local portId
-> RpcPortBindingIfId / RpcPortBindingSvc / RpcPortFilter / Open[Name]Endpoint
-> RPC endpoint mapper or SCM lookup
-> RpcBindingToStringBindingW
-> EpMapper_CopyNcalrpcEndpoint
-> EPMAPPER_GET_PORT_NAME_RPL.wszPortName
-> StoreLpcPortName bounded cache copy
```

Driver boundary:

```text
SbieSvc API_OPEN_DYNAMIC_PORT
-> driver Ipc_CopyFixedUserWString
-> fixed IPC_DYNAMIC_PORT.wstrPortId / wstrPortName
```

## Logic Risk

The old code mixed two different contracts: fixed-size wire fields and
null-terminated C strings. That works only if every producer is honest and every
endpoint string has the exact observed example shape. This is the wrong trust
boundary for a service request. The local service must treat the message field
as a bounded field first, and only then turn it into a string.

The `RpcBindingToStringBindingW` issue is a topology error rather than only a
copy bug: the RPC runtime returns a string-binding representation, and the
endpoint is a named field inside that representation. Extracting it by a magic
offset and hard-coded observed endpoint length can misparse non-matching or
future local-RPC strings.

## Fix

`rpcrt.c` now uses `RpcRt_CopyFixedWString` before sending
`EPMAPPER_GET_PORT_NAME_REQ` and before caching `IPC_DYNAMIC_PORT` entries.
Oversized, empty, or unterminated port ids and port names fail before they cross
or enter fixed local storage.

`EpMapperServer.cpp` now uses `EpMapper_CopyFixedWString` to validate and copy
`req->wszPortId` into local `portId` before any service policy lookup,
configuration lookup, `std::wstring` composition, or driver call. The original
wire field is no longer consumed directly as a C string.

`EpMapperServer.cpp` also replaces the `+ 9` / `wstrPortName[23]` endpoint
parser with `EpMapper_CopyNcalrpcEndpoint`, which validates the `ncalrpc:[`
prefix, finds the closing bracket, copies only the bracketed endpoint, and
rejects endpoint strings that do not fit in the fixed destination.

No endpoint policy, dynamic-port filter id policy, SCM lookup behavior, driver
API shape, or process-id `0` compatibility path changed.

## Acceptance Gate

`docs/plan/check-srev-218.py` validates the draft-07 schema, official
references, fixed wire arrays, bounded request/cached-string copies, service
local `portId` gate before policy use, validated `ncalrpc:[endpoint]` parsing,
removal of stale magic endpoint parsing, split ledger fragment, and continued
driver-side fixed-string copy gate.

Runtime/build gate: Windows service and DLL build, dynamic spooler resolution,
configured `RpcPortBindingIfId` resolution, configured `RpcPortBindingSvc`
resolution, long/empty `RpcPortBinding` tag negative tests, malformed service
message negative test, and repeated endpoint cache lookup proving valid dynamic
ports still resolve and malformed fixed-wire strings fail cleanly.
