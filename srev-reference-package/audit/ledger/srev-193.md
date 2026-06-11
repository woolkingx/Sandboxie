---
kind: srev-ledger-entry
id: SREV-193
title: IE COM Navigation Input Contract
status: patched-source-level-after-official-iwebbrowser2-variant-iuri-and-bstr-ownership-review-needs-windows-runtime-proof
owner: Sandboxie/core/svc/comserver9_ie.c
spec: docs/plan/srev-193-ie-com-navigation-input-contract.md
schema: docs/plan/srev-193-ie-com-navigation-input-contract.schema.json
checker: docs/plan/check-srev-193.py
runtime_gate: Windows SbieSvc build plus IE COM Navigate Navigate2 AggregatedNavigation2 null unsupported variant and .url smoke proof
---
### SREV-193: IE COM Navigation Input Contract

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official `IWebBrowser2`, `VARIANT`, `IUri::GetRawUri`, and BSTR ownership review; needs Windows runtime proof |
| Evidence | `Sandboxie/core/svc/comserver9_ie.c` was the top unnamed reviewable core file after SREV-192. Its IE COM server shim forwards navigation inputs into `IEServer_RestartProgram` and `IEServer_ResolveUrl`. Before this fix, `IWebBrowser2::Navigate2` read `URL->bstrVal` without proving `URL` was non-NULL or that `vt == VT_BSTR`; `IWebBrowser2::Navigate`, `ITargetFramePriv::NavigateHack`, `ITargetFrame2::SetFrameSrc`, and `IOleCommandTarget::Exec` could forward NULL string inputs; `ITargetFramePriv2::AggregatedNavigation2` called `IUri_GetRawUri` without a NULL `pUri` gate and without releasing the returned BSTR. |
| Data | `IWebBrowser2::Navigate`, `IWebBrowser2::Navigate2`, `VARIANT`, `VT_BSTR`, `BSTR`, `IUri::GetRawUri`, `SysFreeString`, `ITargetFramePriv::NavigateHack`, `ITargetFramePriv2::AggregatedNavigation2`, `ITargetFrame2::SetFrameSrc`, `IOleCommandTarget::Exec`, `IEServer_RestartProgram`, and `IEServer_ResolveUrl`. |
| Schema | `IE_COM_NAVIGATION_INPUT_CONTRACT` says the local COM broker only supports non-NULL URL/path strings for restart, `Navigate2` must prove the active variant member before reading `bstrVal`, `IUri_GetRawUri` output is caller-owned, and the service binary must link `OleAut32.lib` when using `SysFreeString`. |
| Topology | Legal flow is `COM caller navigation input -> method-specific shape gate -> non-NULL URL/path string -> optional .url resolution -> ComServer_RestartProgram`. Legal `IUri` flow is `IUri pointer -> IUri_GetRawUri out BSTR -> NavigateHack read-only use -> SysFreeString`. |
| Logic Risk | Reading a VARIANT union member without checking `vt`, forwarding NULL strings into string-scanning code, and leaking BSTR ownership are boundary errors at the COM broker edge. The full `Navigate2` PIDL shape remains unsupported; this patch rejects unsupported variants instead of treating them as BSTR. |
| Official Shape | `docs/plan/srev-193-ie-com-navigation-input-contract.md` records Microsoft `IWebBrowser2::Navigate`, `IWebBrowser2::Navigate2`, VARIANT manipulation, `IUri::GetRawUri`, and `SysFreeString` references. `docs/plan/srev-193-ie-com-navigation-input-contract.schema.json` records the JSON Schema draft-07 local `IE_COM_NAVIGATION_INPUT_CONTRACT` contract. |
| Fix | `comserver9_ie.c` now rejects NULL navigation strings, checks `URL != NULL`, `URL->vt == VT_BSTR`, and `URL->bstrVal != NULL` before `Navigate2` reads the BSTR member, rejects a NULL `IUri *`, frees `IUri_GetRawUri` output with `SysFreeString`, and keeps a final NULL guard in `IEServer_RestartProgram`. `comserver9.c` includes `oleauto.h`, and `SboxSvc.vcxproj` links `OleAut32.lib` in every service configuration. |
| Acceptance Gate | `docs/plan/check-srev-193.py` validates the draft-07 schema, official references, source gates, stale unchecked `Navigate2` shape removal, `IUri_GetRawUri` ownership release, `oleauto.h` include, `OleAut32.lib` project dependency coverage, and split ledger fragment; `docs/plan/check-srev-193.sh` is the matrix wrapper. Runtime gate: Windows SbieSvc build plus IE COM `Navigate`, `Navigate2` `VT_BSTR`, NULL/unsupported `Navigate2`, `AggregatedNavigation2`, and `.url` smoke proof. |
