# SREV-052: DNS Filter IP Entry Ownership

## Data

`Sandboxie/core/dll/dns_filter.c` parses `NetworkDnsFilter` configuration into a
pattern and an optional semicolon-separated IP list. Each parsed IP address is
represented by an allocated `IP_ENTRY`.

## Official Shape

The local `_inet_xton` helper wraps IP text parsing and follows the usual
`InetPtonW` success shape: return `1` for a valid parsed IPv4/IPv6 address and
`0` for invalid text.

```text
https://learn.microsoft.com/en-us/windows/win32/api/ws2tcpip/nf-ws2tcpip-inetptonw
```

## Schema

Local schema:

```text
docs/plan/srev-052-dns-filter-ip-entry-ownership.schema.json
```

An `IP_ENTRY` candidate has one of two legal ownership transitions:

```text
valid parse   -> entries list owns IP_ENTRY
invalid parse -> parser frees IP_ENTRY
```

## Topology

```text
NetworkDnsFilter config -> _inet_xton parse -> IP_ENTRY ownership transfer
```

The config parser owns allocation until the entry is inserted into the list.

## Logic Risk

Before this patch, the parser allocated an `IP_ENTRY` before `_inet_xton`.
Invalid IP text skipped insertion but did not free the allocated entry. Bad
configuration therefore leaked one `IP_ENTRY` per invalid token during DNS
filter initialization.

## Fix

Invalid parsed entries are now freed. Synthetic IPv4-mapped IPv6 entries also
check allocation before initialization and list insertion.

## Acceptance Gate

`docs/plan/check-srev-052.py` validates the draft-07 schema, official reference,
invalid-entry free path, allocation checks, and ledger entry.

Windows gate: load `NetworkDnsFilter` with valid IPv4, valid IPv6, invalid
tokens, and mixed lists; verify valid entries still filter DNS while invalid
tokens do not grow process heap across repeated initialization.
