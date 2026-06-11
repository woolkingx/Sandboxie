# SREV-204: HTIFACE7 IE COM ABI Boundary

## Stage

schema -> boundary -> topology -> logic -> verify

## Evidence

`Sandboxie/core/svc/htiface7.h` was the top unnamed reviewable core file after
SREV-203. The checker ranked it highly because the header contains NT/COM text
and URI property names such as `Uri_PROPERTY_PASSWORD`. Local review shows this
is not a Protected Storage or credential-store implementation. It is an IE 7
COM ABI projection for `IUri` and a private `ITargetFramePriv2` interface used
by the IE COM restart shim.

The only local consumer is `Sandboxie/core/svc/comserver9.c` including the
header for `Sandboxie/core/svc/comserver9_ie.c`. The consumer-side input and
BSTR ownership issues for `IUri::GetRawUri` were already patched in SREV-193.

## Data

`htiface7.h`, `IUri`, `Uri_PROPERTY`, `Uri_PROPERTY_PASSWORD`,
`IUri_GetRawUri`, `IUri_GetPassword`, `ITargetFramePriv2`,
`ITargetFramePriv2_NavigateHack`, `ITargetFramePriv2_AggregatedNavigation2`,
`comserver9.c`, `comserver9_ie.c`, and SREV-193.

## Official Shape

Microsoft documents `IUri` as an Internet Explorer 7 URLMON interface for
parsing and building URIs. The documented method list includes `GetRawUri`,
`GetPassword`, `GetUserInfo`, and other URI property accessors. Microsoft also
documents `CreateUri` as creating an `IUri` instance from a URI string.

The `password` signal in this file is therefore URI syntax data, not Windows
credential storage. The official `IUri` boundary is a COM interface and BSTR
output boundary; local policy belongs in the IE COM shim that consumes it, not
in this copied ABI header.

No current Microsoft Learn page was found for `ITargetFramePriv2`; it is treated
as an IE private compatibility interface. That makes the header an external ABI
projection. Changing its vtable shape would be riskier than changing the local
consumer gates.

References:

- `https://learn.microsoft.com/en-us/previous-versions/windows/internet-explorer/ie-developer/platform-apis/ms775038(v=vs.85)`
- `https://learn.microsoft.com/en-us/previous-versions/windows/internet-explorer/ie-developer/platform-apis/ms775098(v=vs.85)`
- `https://learn.microsoft.com/en-us/windows/win32/api/oleauto/nf-oleauto-sysfreestring`
- `docs/plan/srev-193-ie-com-navigation-input-contract.md`

## Schema

`HTIFACE7_IE_COM_ABI_BOUNDARY` says:

- `htiface7.h` is an external IE COM ABI projection, not a local policy owner.
- `Uri_PROPERTY_PASSWORD` is a URI component property, not Protected Storage or
  credential-store data.
- `IUri` official shape comes from URLMON/IE documentation.
- `ITargetFramePriv2` is private compatibility ABI and should be handled as
  observed external ABI, not redefined locally.
- Local safety gates belong in `comserver9_ie.c` consumers, with SREV-193 as
  the active consumer fix.
- This SREV intentionally makes no source mutation.

## Topology

```text
IE COM caller
-> ITargetFramePriv / ITargetFramePriv2 / IUri ABI declared by htiface7.h
-> comserver9_ie.c consumer methods
-> SREV-193 input/BSTR gates
-> ComServer restart / URL resolution
```

## Logic Risk

Without this classification, the coverage queue can misread the header's
`password` strings as credential-store risk and push future work toward editing
a copied ABI header. That would attack the wrong owner. The real policy and
memory-safety boundary is the local consumer that receives an `IUri *` or
navigation strings.

## Fix

No source mutation. This entry records `htiface7.h` as reviewed and links its
active local consumer risk to SREV-193.

## Acceptance Gate

`docs/plan/check-srev-204.py` validates the draft-07 schema, official
references, header ABI tokens, consumer coordinates, SREV-193 linkage, split
ledger fragment, and absence of a source patch requirement. Runtime/build gate:
covered by SREV-193 IE COM navigation smoke unless future work changes
`htiface7.h` or its consumer ABI.
