---
kind: srev-ledger-entry
id: SREV-314
title: NSI Network Change Notification Shim
status: patched source-level comments after official network-change notification, NSI service, and RPC return shape; needs Windows runtime proof
owner: Sandboxie/core/dll/custom.c
spec: docs/plan/srev-314-nsi-network-change-notification-shim.md
schema: docs/plan/srev-314-nsi-network-change-notification-shim.schema.json
checker: docs/plan/check-srev-314.py
runtime_gate: Windows WinINet/NSI smoke proving compatibility without broader NSI RPC access
---

### SREV-314: NSI Network Change Notification Shim

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | patched source-level comments after official network-change notification, NSI service, and RPC return shape; needs Windows runtime proof |
| Evidence | `ldr.c` registers `winnsi.dll` with `NsiRpc_Init`. `NsiRpc_Init` resolves the private export `NsiRpcRegisterChangeNotification` and hooks it. `NsiRpc_NsiRpcRegisterChangeNotification` calls the native export, changes only `EPT_S_NOT_REGISTERED` to `NO_ERROR`, and returns every other native result unchanged. |
| Data | `winnsi.dll`, `NsiRpc_Init`, `Ldr_GetProcAddrNew("NsiRpcRegisterChangeNotification")`, `SBIEDLL_HOOK(NsiRpc_, NsiRpcRegisterChangeNotification)`, `NsiRpc_NsiRpcRegisterChangeNotification`, `__sys_NsiRpcRegisterChangeNotification`, `EPT_S_NOT_REGISTERED`, `NO_ERROR`, WinINet, NSI service notifications, and endpoint mapper miss behavior. |
| Schema | `NSI_NETWORK_CHANGE_NOTIFICATION_SHIM` says `NsiRpc_NsiRpcRegisterChangeNotification` owns only a private winnsi compatibility result mapping; public network-change notification ownership belongs to documented NetIO/IP Helper APIs and the NSI service; the shim calls the native export before mapping results; only `EPT_S_NOT_REGISTERED` may be translated to `NO_ERROR`; every other native `RPC_STATUS` must pass through unchanged; this SREV changes comments and proof only, not NSI RPC access policy. |
| Topology | `winnsi.dll load -> Ldr_Dlls entry -> NsiRpc_Init -> Ldr_GetProcAddrNew("NsiRpcRegisterChangeNotification") -> SBIEDLL_HOOK -> NsiRpc_NsiRpcRegisterChangeNotification -> native private export result -> EPT_S_NOT_REGISTERED becomes NO_ERROR -> every other result passes through unchanged`. |
| Logic Risk | A broad WinINet workaround comment can misroute future changes toward opening wider NSI RPC access. The current source does not prove that topology. The safer owner boundary is result-mapping only: native path first, endpoint-map miss suppression only, all other return values intact. |
| Official Shape | Microsoft documents public IP-interface change notification through `NotifyIpInterfaceChange`, cancellation through `CancelMibChangeNotify2`, the Network Store Interface service as delivering network notifications to user-mode clients, and `EPT_S_NOT_REGISTERED` as no more endpoints available from the endpoint-map database. |
| Fix | `ldr.c` now names the `winnsi.dll` entry as the SREV-314 private NSI network-change notification shim. `custom.c` now describes the exact result mapping and the NSI boundary. No hook registration condition, export name, native call, argument forwarding, or return-value policy changed. |
| Acceptance Gate | `docs/plan/check-srev-314.py` validates the draft-07 schema, official references, loader table registration, private-export lookup, `SBIEDLL_HOOK`, native call before mapping, `EPT_S_NOT_REGISTERED -> NO_ERROR` translation, pass-through return, source comment boundary, combined ledger entry, and split ledger fragment; `docs/plan/check-srev-314.sh` is the targeted wrapper. Runtime gate: Windows WinINet/NSI smoke proving certificate-revocation/network initialization compatibility remains acceptable while no broader NSI RPC access is granted by this hook. |
