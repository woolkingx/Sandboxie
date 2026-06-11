---
kind: srev-ledger-entry
id: SREV-053
title: DNS Filter Begin Constructor Boundary
status: patched-source-level-after-official-wsalookupservicebeginw-wsaquerysetw-and-loca
owner: Sandboxie/core/dll/dns_filter.c
spec: docs/plan/srev-053-dns-filter-begin-constructor.md
schema: docs/plan/srev-053-dns-filter-begin-constructor.schema.json
checker: docs/plan/check-srev-053.py
runtime_gate: filtered A/AAAA lookup success, null output pointer fallthrough, allocation-failure injection for lowercase buffer/fake handle/map/domain/service-class state, and End cleanup after successful fake lookup
---
### SREV-053: DNS Filter Begin Constructor Boundary

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official WSALookupServiceBeginW/WSAQUERYSETW and local fake lookup owner analysis; needs Windows DNS filter allocation-failure proof |
| Evidence | `Sandboxie/core/dll/dns_filter.c` `WSA_WSALookupServiceBeginW` assigned `*lphLookup = fakeHandle` before proving that `WSA_GetLookup`, `DomainName`, optional `ServiceClassId`, and entry/no-more state were all valid. If state construction failed, the hook could still return `NO_ERROR` with an unmapped or incomplete fake handle. The filtered path also dereferenced `lphLookup` without checking whether the caller supplied an output pointer. |
| Data | Caller `WSAQUERYSETW` restriction, matched DNS filter pattern, fake lookup handle, `WSA_LOOKUP` map state, `DomainName`, optional `ServiceClassId`, namespace, and filtered entries/no-more state. |
| Schema | `DNS_FILTER_BEGIN_CONSTRUCTOR` says the fake lookup handle may cross the API boundary only after complete `WSA_LOOKUP` state is constructed, and allocation failure must return `SOCKET_ERROR`/`WSA_NOT_ENOUGH_MEMORY` with no caller-visible fake handle or leaked map state. |
| Topology | `WSAQUERYSETW` restriction flows into the DNS filter match; the hook constructs owner-local `WSA_LOOKUP` state; only the completed fake handle crosses back to the caller and later `Next`/`End` paths. |
| Logic Risk | A handle is a capability. Publishing it before its owner state exists makes later behavior depend on partial allocation success, and can turn memory pressure into wrong DNS A/AAAA routing, late `Next` failure, or an invalid-handle state drift. |
| Official Shape | `docs/plan/srev-053-dns-filter-begin-constructor.md` records Microsoft `WSALookupServiceBeginW` and `WSAQUERYSETW` references. `docs/plan/srev-053-dns-filter-begin-constructor.schema.json` records the JSON Schema draft-07 local `DNS_FILTER_BEGIN_CONSTRUCTOR` contract. |
| Fix | The filtered path now requires non-null `lphLookup`, checks the lowercase buffer allocation, constructs fake lookup state transactionally, cleans up inserted map state and owned allocations on failure, returns the Winsock memory error code, and assigns `*lphLookup` only after `DomainName`, optional `ServiceClassId`, and entries/no-more state are valid. |
| Acceptance Gate | `docs/plan/check-srev-053.py` validates the draft-07 schema, official references, output-pointer gate, allocation gates, transactional cleanup, delayed handle publication, Winsock memory error code, and ledger entry; `docs/plan/check-srev-053.sh` is the matrix wrapper. Windows gate: filtered A/AAAA lookup success, null output pointer fallthrough, allocation-failure injection for lowercase buffer/fake handle/map/domain/service-class state, and End cleanup after successful fake lookup. |
