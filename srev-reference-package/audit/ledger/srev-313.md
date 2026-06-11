---
kind: srev-ledger-entry
id: SREV-313
title: HNet Firewall Dynamic Port Shim
status: patched source-level after official Windows Firewall and HRESULT shape; needs Windows runtime proof
owner: Sandboxie/core/dll/netapi.c
spec: docs/plan/srev-313-hnet-firewall-dynamic-port-shim.md
schema: docs/plan/srev-313-hnet-firewall-dynamic-port-shim.schema.json
checker: docs/plan/check-srev-313.py
runtime_gate: Windows bind/firewall smoke proving sandboxed bind compatibility and no host firewall open-port policy mutation
---

### SREV-313: HNet Firewall Dynamic Port Shim

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | patched source-level after official Windows Firewall and HRESULT shape; needs Windows runtime proof |
| Evidence | `ldr.c` registers `hnetcfg.dll` with `HNet_Init`. `HNet_Init` resolves the private export `IcfOpenDynamicFwPort` and hooks it when present. `HNet_IcfOpenDynamicFwPort` does not call the native export; it returns success to preserve the caller's bind path without changing host firewall policy. |
| Data | `hnetcfg.dll`, `HNet_Init`, `GetProcAddress("IcfOpenDynamicFwPort")`, `SBIEDLL_HOOK(HNet_, IcfOpenDynamicFwPort)`, `HNet_IcfOpenDynamicFwPort`, `S_OK`, Windows Firewall COM policy owners, and host firewall open-port policy. |
| Schema | `HNET_FIREWALL_DYNAMIC_PORT_SHIM` says `HNet_IcfOpenDynamicFwPort` owns only a private hnetcfg compatibility shim; host Windows Firewall policy mutation belongs to Windows Firewall COM policy owners, not a sandboxed process; the shim reports `S_OK` without calling the native export; `HNet_Init` may hook the export only when present; this SREV changes comments and HRESULT spelling only. |
| Topology | `hnetcfg.dll load -> Ldr_Dlls entry -> HNet_Init -> GetProcAddress("IcfOpenDynamicFwPort") -> SBIEDLL_HOOK -> HNet_IcfOpenDynamicFwPort -> S_OK without host firewall mutation`. |
| Logic Risk | Treating this as a generic firewall workaround can misroute future patches toward opening host firewall policy from inside a sandboxed process. The narrower owner boundary is compatibility-only: preserve bind behavior but do not mutate host firewall rules or open-port policy. |
| Official Shape | Microsoft documents Windows Firewall open-port policy through COM interfaces such as `INetFwOpenPort`, documents policy control through `INetFwPolicy2`, and documents HRESULT success through `S_OK`. |
| Fix | `ldr.c` now names the `hnetcfg.dll` entry as the SREV-313 private hnetcfg firewall dynamic-port shim. `HNet_IcfOpenDynamicFwPort` now documents the host firewall policy boundary and returns `S_OK` instead of literal `0`. No hook registration condition, export name, native-call suppression, or caller argument handling changed. |
| Acceptance Gate | `docs/plan/check-srev-313.py` validates the draft-07 schema, official references, loader table registration, private-export lookup, `SBIEDLL_HOOK`, `S_OK` return, absence of a native `__sys_IcfOpenDynamicFwPort` call from the hook body, source comment boundary, combined ledger entry, and split ledger fragment; `docs/plan/check-srev-313.sh` is the targeted wrapper. Runtime gate: Windows bind/firewall smoke proving sandboxed bind compatibility and no host Windows Firewall rule/open-port policy is added. |
