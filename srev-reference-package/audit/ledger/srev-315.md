---
kind: srev-ledger-entry
id: SREV-315
title: SCM DLL Service Start Shim
status: patched source-level comments after official DirectWrite and service-control shape; needs Windows runtime proof
owner: Sandboxie/core/dll/scm_misc.c
spec: docs/plan/srev-315-scm-dll-service-start-shim.md
schema: docs/plan/srev-315-scm-dll-service-start-shim.schema.json
checker: docs/plan/check-srev-315.py
runtime_gate: Windows DirectWrite FontCache smoke plus Office osppc smoke with no readiness-proof claim
---

### SREV-315: SCM DLL Service Start Shim

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | patched source-level comments after official DirectWrite and service-control shape; needs Windows runtime proof |
| Evidence | `ldr.c` registers `dwrite.dll` with `Scm_DWriteDll`. `Scm_DWriteDll` asks `Scm_DllHack` to start `FontCache` if the real service is stopped. The same helper is used by `Scm_OsppcDll` for the Office `osppsvc` path. The helper skips null modules, skips boxed services, queries current service state, opens the service with `SERVICE_START`, calls `StartService`, sleeps briefly only on start-call success, and closes the service handle. |
| Data | `dwrite.dll`, `osppc.dll`, `Scm_DWriteDll`, `Scm_OsppcDll`, `Scm_DllHack`, `FontCache`, `osppsvc`, `Scm_QueryServiceByName`, `SERVICE_STOPPED`, `Scm_IsBoxedService`, `Scm_OpenServiceWImpl`, `SERVICE_START`, `Scm_StartServiceWImpl`, `Sleep(500)`, and `Scm_CloseServiceHandleImpl`. |
| Schema | `SCM_DLL_SERVICE_START_SHIM` says `Scm_DllHack` owns only a DLL-triggered host service-start compatibility request; `Scm_DWriteDll` maps `dwrite.dll` load to the FontCache service-start shim; `Scm_OsppcDll` maps `osppc.dll` load to the `osppsvc` service-start shim; boxed services must not be started through this host shim; `StartServiceW` success must not be treated as proof that the service reached `SERVICE_RUNNING`; this SREV changes comments and proof only, not service-start behavior. |
| Topology | `dwrite.dll load -> Ldr_Dlls entry -> Scm_DWriteDll -> Scm_DllHack("FontCache") -> Scm_QueryServiceByName(..., status) -> state == SERVICE_STOPPED -> Scm_OpenServiceWImpl(..., SERVICE_START) -> Scm_StartServiceWImpl -> optional Sleep(500) -> Scm_CloseServiceHandleImpl`. |
| Logic Risk | Calling this a generic hack hides the boundary that SCM owns service state and start authorization. `StartServiceW` success does not prove full service readiness; a future readiness claim would need bounded `QueryServiceStatusEx` polling and Windows runtime evidence. |
| Official Shape | Microsoft documents DirectWrite font-system services for font enumeration, fallback, and caching. Microsoft documents `OpenServiceW`, `StartServiceW`, `QueryServiceStatusEx`, and service access rights as the legal SCM/service-control shape. |
| Fix | Source comments now name `Scm_DllHack` as a service-start compatibility shim and record that `StartServiceW` only proves SCM accepted the start request, not that the service reached `SERVICE_RUNNING`. The `dwrite.dll` loader entry now names the DirectWrite FontCache service-start shim, and the Office/FontCache consumer comments no longer use generic hack wording. No query, boxed-service skip, open access mask, start call, sleep duration, handle close, or service name changed. |
| Acceptance Gate | `docs/plan/check-srev-315.py` validates the draft-07 schema, official references, loader table registration, `Scm_DWriteDll -> Scm_DllHack(FontCache)` topology, shared helper query/start/close behavior, boxed-service skip, `SERVICE_STOPPED` gate, `SERVICE_START` access, source comments, absence of old generic hack wording in this owner block, combined ledger entry, and split ledger fragment; `docs/plan/check-srev-315.sh` is the targeted wrapper. Runtime gate: Windows DirectWrite/IE 9 FontCache smoke plus Office osppc smoke proving compatibility is preserved and no caller treats this helper as proof of full `SERVICE_RUNNING` readiness. |
