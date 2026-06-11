---
kind: srev-ledger-entry
id: SREV-050
title: DNS Filter Response Buffer Gates
status: patched-source-level-after-official-wsalookupservicenextw-wsaquerysetw-blob-and-
owner: Sandboxie/core/dll/dns_filter.c
spec: docs/plan/srev-050-dns-filter-response-buffer.md
schema: docs/plan/srev-050-dns-filter-response-buffer.schema.json
checker: docs/plan/check-srev-050.py
runtime_gate: filtered A/AAAA responses with exact-size, undersized, oversized, long-domain, and many-address output buffers
---
### SREV-050: DNS Filter Response Buffer Gates

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official WSALookupServiceNextW/WSAQUERYSETW/BLOB and local DNS response packer analysis; needs Windows DNS filter malformed-buffer proof |
| Evidence | `Sandboxie/core/dll/dns_filter.c` `WSA_FillResponseStructure` builds a synthetic `WSAQUERYSETW` result into caller memory. The source already had segment-level `CHECK_BUFFER_SPACE` calls and a final comment saying the end check is a failsafe if size calculations are wrong, but the segment checks compiled only under `_DEBUG`. Release builds therefore trusted the precomputed `neededSize` until after the response was written. |
| Data | Caller `lpqsResults` buffer, `lpdwBufferLength` byte capacity, filtered DNS address entries, packed `WSAQUERYSETW`, `CSADDR_INFO`, `SOCKADDR`, `BLOB`, `HOSTENT`, and relative HOSTENT payloads. |
| Schema | `DNS_FILTER_WSAQUERYSET_RESPONSE_BUFFER` requires every packed segment write to prove remaining capacity against `bufferEnd` in release builds. `lpdwBufferLength` owns the output buffer byte capacity and required-size result on `WSAEFAULT`. |
| Topology | Filtered DNS entries flow into `WSA_FillResponseStructure`; the hook writes one synthetic Winsock result into the caller `lpqsResults` buffer. Winsock owns the ABI/error contract. |
| Logic Risk | A final bounds check after writes can detect only after-the-fact drift. If the size formula and write layout diverge, a release build could corrupt caller memory before returning `WSAEFAULT`. |
| Official Shape | `docs/plan/srev-050-dns-filter-response-buffer.md` records Microsoft `WSALookupServiceNextW`, `WSAQUERYSETW`, and `BLOB` references. `docs/plan/srev-050-dns-filter-response-buffer.schema.json` records the JSON Schema draft-07 local `DNS_FILTER_WSAQUERYSET_RESPONSE_BUFFER` contract. |
| Fix | `CHECK_BUFFER_SPACE` now runs in all builds, uses a subtractive remaining-capacity check, and `bufferEnd` is available outside `_DEBUG`. The final end check remains as SREV-050 diagnostic defense and now uses the same `bufferEnd` owner. |
| Acceptance Gate | `docs/plan/check-srev-050.py` validates the draft-07 schema, official references, release-mode buffer gate, unconditional `bufferEnd`, diagnostic final-fence ownership, removal of the old `_DEBUG` no-op gate, SREV-263 adjacency, and ledger entry; `docs/plan/check-srev-050.sh` is the targeted wrapper. Windows gate: filtered A/AAAA responses with exact-size, undersized, oversized, long-domain, and many-address output buffers. |
