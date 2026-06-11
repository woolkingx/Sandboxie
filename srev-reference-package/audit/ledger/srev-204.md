---
kind: srev-ledger-entry
id: SREV-204
title: HTIFACE7 IE COM ABI Boundary
status: classified-source-level-no-local-mutation-after-official-ie-uri-shape-review
owner: Sandboxie/core/svc/htiface7.h
consumer: Sandboxie/core/svc/comserver9_ie.c
spec: docs/plan/srev-204-htiface7-ie-com-abi-boundary.md
schema: docs/plan/srev-204-htiface7-ie-com-abi-boundary.schema.json
checker: docs/plan/check-srev-204.py
runtime_gate: Covered by SREV-193 IE COM navigation smoke unless future work changes htiface7.h or its consumer ABI
---

### SREV-204: HTIFACE7 IE COM ABI Boundary

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | classified source-level; no local mutation after official IE IUri shape review |
| Evidence | `Sandboxie/core/svc/htiface7.h` was the top unnamed reviewable core file after SREV-203. It contains IE 7 `IUri` and private `ITargetFramePriv2` COM ABI definitions. The high password score comes from URI property names such as `Uri_PROPERTY_PASSWORD`, not Protected Storage or Windows credential-store data. The only local consumer is the IE COM restart shim in `Sandboxie/core/svc/comserver9_ie.c`, included through `Sandboxie/core/svc/comserver9.c`. |
| Data | `htiface7.h`, `IUri`, `Uri_PROPERTY`, `Uri_PROPERTY_PASSWORD`, `IUri_GetRawUri`, `IUri_GetPassword`, `ITargetFramePriv2`, `ITargetFramePriv2_NavigateHack`, `ITargetFramePriv2_AggregatedNavigation2`, `comserver9.c`, `comserver9_ie.c`, and SREV-193. |
| Schema | `HTIFACE7_IE_COM_ABI_BOUNDARY` says `htiface7.h` is an external IE COM ABI projection, not a local policy owner; `Uri_PROPERTY_PASSWORD` is a URI component property; `IUri` official shape comes from URLMON/IE documentation; `ITargetFramePriv2` is private compatibility ABI; local safety gates belong in `comserver9_ie.c`; and SREV-193 is the active consumer fix. |
| Topology | Legal flow is `IE COM caller -> ITargetFramePriv / ITargetFramePriv2 / IUri ABI declared by htiface7.h -> comserver9_ie.c consumer methods -> SREV-193 input/BSTR gates -> ComServer restart / URL resolution`. |
| Logic Risk | Without this classification, future coverage work can misread `password` as credential-store risk and edit a copied ABI header instead of the local consumer. That would target the wrong owner and risk COM vtable drift. |
| Official Shape | `docs/plan/srev-204-htiface7-ie-com-abi-boundary.md` records Microsoft `IUri`, `CreateUri`, `SysFreeString`, and SREV-193 consumer references. `docs/plan/srev-204-htiface7-ie-com-abi-boundary.schema.json` records the JSON Schema draft-07 local `HTIFACE7_IE_COM_ABI_BOUNDARY` contract. |
| Fix | No source mutation. The header is classified as reviewed external ABI, and its active local consumer risk remains owned by SREV-193. |
| Acceptance Gate | `docs/plan/check-srev-204.py` validates the draft-07 schema, official references, header ABI tokens, consumer coordinates, SREV-193 linkage, split ledger fragment, and absence of a source patch requirement; `docs/plan/check-srev-204.sh` is the targeted wrapper. Runtime/build gate: covered by SREV-193 IE COM navigation smoke unless future work changes `htiface7.h` or its consumer ABI. |
