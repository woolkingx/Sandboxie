---
kind: srev-ledger-entry
id: SREV-052
title: DNS Filter IP Entry Ownership
status: patched-source-level-after-local-networkdnsfilter-parser-and-inetpton-style-pars
owner: Sandboxie/core/dll/dns_filter.c
spec: docs/plan/srev-052-dns-filter-ip-entry-ownership.md
schema: docs/plan/srev-052-dns-filter-ip-entry-ownership.schema.json
checker: docs/plan/check-srev-052.py
runtime_gate: valid IPv4, valid IPv6, invalid tokens, mixed lists, and repeated initialization heap behavior
---
### SREV-052: DNS Filter IP Entry Ownership

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | patched source-level after local NetworkDnsFilter parser and InetPton-style parse result analysis; needs Windows DNS filter invalid-config heap proof |
| Evidence | `Sandboxie/core/dll/dns_filter.c` `WSA_InitNetDnsFilter` allocated an `IP_ENTRY` before calling `_inet_xton`. When `_inet_xton` failed to parse an invalid IP token, the entry was neither inserted into the list nor freed. The IPv4-mapped IPv6 synthetic allocation also initialized the entry before checking allocation success. |
| Data | `NetworkDnsFilter` IP tokens, `_inet_xton` parse result, allocated `IP_ENTRY`, and parser-owned entries list. |
| Schema | `DNS_FILTER_IP_ENTRY_OWNERSHIP` says a valid parsed `IP_ENTRY` transfers to the entries list; an invalid parsed `IP_ENTRY` remains parser-owned and must be freed. |
| Topology | Configuration token flows through `_inet_xton`; only successful parse crosses into the runtime entries list. |
| Logic Risk | Invalid configuration should be rejected/skipped as data, not converted into leaked heap objects during initialization. |
| Official Shape | `docs/plan/srev-052-dns-filter-ip-entry-ownership.md` records Microsoft `InetPtonW` return shape as the external parse analogue. `docs/plan/srev-052-dns-filter-ip-entry-ownership.schema.json` records the JSON Schema draft-07 local `DNS_FILTER_IP_ENTRY_OWNERSHIP` contract. |
| Fix | Invalid parsed entries are freed, and synthetic IPv4-mapped IPv6 entries check allocation before initialization and list insertion. |
| Acceptance Gate | `docs/plan/check-srev-052.py` validates the draft-07 schema, official reference, invalid-entry free path, allocation checks, and ledger entry; `docs/plan/check-srev-052.sh` is the matrix wrapper. Windows gate: valid IPv4, valid IPv6, invalid tokens, mixed lists, and repeated initialization heap behavior. |
