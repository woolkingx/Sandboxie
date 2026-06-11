---
kind: srev-ledger-entry
id: SREV-051
title: DNS Filter CSADDR_INFO Alignment
status: patched-source-level-after-official-wsaquerysetw-csaddr-info-and-local-packed-bu
owner: Sandboxie/core/dll/dns_filter.c
spec: docs/plan/srev-051-dns-filter-csaddr-alignment.md
schema: docs/plan/srev-051-dns-filter-csaddr-alignment.schema.json
checker: docs/plan/check-srev-051.py
runtime_gate: filtered A/AAAA responses with odd/even domain lengths on x86, x64, and ARM64/ARM64EC
---
### SREV-051: DNS Filter CSADDR_INFO Alignment

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official WSAQUERYSETW/CSADDR_INFO and local packed-buffer alignment analysis; needs Windows DNS filter alignment proof |
| Evidence | `Sandboxie/core/dll/dns_filter.c` packs two WCHAR strings before assigning `lpqsResults->lpcsaBuffer = (PCSADDR_INFO)currentPtr`. `WSAQUERYSETW.lpcsaBuffer` points to `CSADDR_INFO[]`, and `CSADDR_INFO` contains pointer-bearing `SOCKET_ADDRESS` members. Without aligning after the WCHAR strings, the packed cursor can be only 2-byte-aligned before writing pointer fields. |
| Data | Caller `lpqsResults` buffer, packed service/query strings, `CSADDR_INFO[]`, `SOCKET_ADDRESS`, and subsequent `SOCKADDR`/`BLOB` payloads. |
| Schema | `DNS_FILTER_CSADDR_ALIGNMENT` requires the required-size formula and runtime cursor to align to `sizeof(void*)` before the `CSADDR_INFO[]` segment. |
| Topology | DNS strings flow first, then the aligned `CSADDR_INFO[]` segment is exposed through `WSAQUERYSETW.lpcsaBuffer`. |
| Logic Risk | The packed response is an ABI object. Writing pointer-bearing `CSADDR_INFO` fields through an unaligned cursor can break on strict-alignment targets and makes the size formula diverge from the legal runtime layout. |
| Official Shape | `docs/plan/srev-051-dns-filter-csaddr-alignment.md` records Microsoft `WSAQUERYSETW` and `CSADDR_INFO` references. `docs/plan/srev-051-dns-filter-csaddr-alignment.schema.json` records the JSON Schema draft-07 local `DNS_FILTER_CSADDR_ALIGNMENT` contract. |
| Fix | Added `ALIGN_SIZE` for size calculation and aligned both `neededSize` and `currentPtr` before the `CSADDR_INFO[]` segment. |
| Acceptance Gate | `docs/plan/check-srev-051.py` validates the draft-07 schema, official references, `ALIGN_SIZE`, required-size alignment before `csaddrSize`, runtime alignment before `lpcsaBuffer`, and ledger entry; `docs/plan/check-srev-051.sh` is the matrix wrapper. Windows gate: filtered A/AAAA responses with odd/even domain lengths on x86, x64, and ARM64/ARM64EC. |
