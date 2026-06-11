# SREV-053: DNS Filter Begin Constructor Boundary

## Data

`Sandboxie/core/dll/dns_filter.c` `WSA_WSALookupServiceBeginW` intercepts
matched DNS lookups and returns a fake lookup handle. That handle is later
consumed by `WSA_WSALookupServiceNextW` and `WSA_WSALookupServiceEnd`.

The local state attached to the handle is:

```text
fakeHandle
WSA_LOOKUP
Filtered flag
DomainName
optional ServiceClassId
Namespace
Pattern_Aux entries or NoMore
```

## Official Shape

Microsoft documents `WSALookupServiceBeginW` as initiating a query constrained
by `WSAQUERYSETW` and returning only a handle used by later
`WSALookupServiceNext` calls:

```text
https://learn.microsoft.com/en-us/windows/win32/api/winsock2/nf-winsock2-wsalookupservicebeginw
```

The same page documents `lphLookup` as an output handle and says failure returns
`SOCKET_ERROR`, with `WSA_NOT_ENOUGH_MEMORY` for insufficient memory.

Microsoft documents `WSAQUERYSETW` as carrying `lpszServiceInstanceName`,
`lpServiceClassId`, and `dwNameSpace` query data:

```text
https://learn.microsoft.com/en-us/windows/win32/api/winsock2/ns-winsock2-wsaquerysetw
```

## Schema

Local schema:

```text
docs/plan/srev-053-dns-filter-begin-constructor.schema.json
```

The fake lookup handle may cross to the caller only after every owned state field
needed by later `Next` and `End` paths has been constructed or deliberately set
to `NoMore`.

## Topology

```text
WSAQUERYSETW restriction -> DNS filter match -> WSA_LOOKUP state -> caller handle
```

The hook owns synthetic lookup state. Winsock owns the external Begin/Next/End
ABI shape. The caller owns only the output handle after successful construction.

## Logic Risk

Before this patch, the hook assigned `*lphLookup = fakeHandle` before proving
that `WSA_LOOKUP`, `DomainName`, and optional `ServiceClassId` were available.
If construction failed, the hook could still return `NO_ERROR` with an unmapped
or incomplete fake handle. A missing `DomainName` would make the filtered `Next`
path fail later, and a missing `ServiceClassId` could change A/AAAA routing.

The hook also dereferenced `lphLookup` in the filtered path without first
checking that the caller supplied an output pointer.

## Fix

The filtered path now requires `lphLookup` before intercepting, checks the
temporary lowercase buffer allocation, constructs the fake handle and
`WSA_LOOKUP` state transactionally, and assigns `*lphLookup` only after
`DomainName`, optional `ServiceClassId`, and entry/no-more state are valid.

Allocation failures remove any inserted map state, free owned allocations, and
return `SOCKET_ERROR` with `WSA_NOT_ENOUGH_MEMORY`.

## Acceptance Gate

`docs/plan/check-srev-053.py` validates the draft-07 schema, official reference
links, `lphLookup` gate, allocation gates, transactional cleanup, delayed handle
publication, Winsock memory error code, and ledger entry.

Windows gate: filtered DNS lookups should return a fake handle only when the
lookup state is complete. Injected allocation failures should return
`SOCKET_ERROR`/`WSA_NOT_ENOUGH_MEMORY` without leaving a caller-visible fake
handle or leaked map entry. A null `lphLookup` should fall through to the real
Winsock implementation for API-owned validation.
