---
kind: srev-ledger-entry
id: SREV-172
title: SetupAPI Driver Install Status
status: patched-source-level-after-official-verifycatalogfile-and-cfgmgr32-configret-review-needs-windows-installer-runtime-proof
owner: Sandboxie/core/dll/setup.c
spec: docs/plan/srev-172-setupapi-driver-install-status.md
schema: docs/plan/srev-172-setupapi-driver-install-status.schema.json
checker: docs/plan/check-srev-172.py
runtime_gate: "Windows DLL build, catalog verification status smoke, CfgMgr32 driver package blocked-install smoke, and installer compatibility observation"
---

### SREV-172: SetupAPI Driver Install Status

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official `VerifyCatalogFile` and CfgMgr32 `CONFIGRET` review; needs Windows installer runtime proof |
| Evidence | `Sandboxie/core/dll/setup.c` was the highest-ranked unnamed reviewable core file after SREV-171. `ldr.c` registers `Setup_Init_CfgMgr32` for `cfgmgr32.dll` and `Setup_Init_SetupApi` for `setupapi.dll`. `setup.c` hooks `VerifyCatalogFile`, `CM_Add_Driver_PackageW`, and `CM_Add_Driver_Package_ExW`. Before this SREV, `Setup_VerifyCatalogFile` converted most nonzero verification errors into `ERROR_SUCCESS`, and both `CM_Add_Driver_Package*` hooks logged `SBIE2205` while returning `0`, which is the `CR_SUCCESS` shape for CfgMgr32-style status. |
| Data | `Sandboxie/core/dll/setup.c`, `Sandboxie/core/dll/ldr.c`, `Setup_Init_SetupApi`, `Setup_VerifyCatalogFile`, `VerifyCatalogFile`, `Setup_Init_CfgMgr32`, `CM_Add_Driver_PackageW`, `CM_Add_Driver_Package_ExW`, `Setup_CM_Add_Driver_PackageW`, `Setup_CM_Add_Driver_Package_ExW`, `SbieApi_Log`, `SBIE2205`, `ERROR_SUCCESS`, `ERROR_AUTHENTICODE_TRUSTED_PUBLISHER`, `CR_SUCCESS`, `CR_ACCESS_DENIED`, and `CONFIGRET`. |
| Schema | `SETUPAPI_DRIVER_INSTALL_STATUS` says `setup.c` owns SetupAPI catalog verification and CfgMgr32 driver-package hook status projection; `VerifyCatalogFile` result values are owned by the original SetupAPI function and verification failure must not be converted into `ERROR_SUCCESS`; `CM_Add_Driver_PackageW` and `CM_Add_Driver_Package_ExW` are blocked driver-package install edges and must return a non-success `CONFIGRET`; `CR_ACCESS_DENIED` is the local blocked status; this SREV does not change hook installation, message `2205`, function-pointer parameter count, dynamic export lookup, or disabled setup/remove hooks; Linux source gates are not Windows installer compatibility proof. |
| Topology | `setupapi.dll` load flows to `Setup_Init_SetupApi`, `VerifyCatalogFile` hook, and original verifier status returned unchanged. `cfgmgr32.dll` load flows to `Setup_Init_CfgMgr32`, optional `CM_Add_Driver_PackageW` / `CM_Add_Driver_Package_ExW` hooks, `SBIE2205` warning on attempted driver package install, and `CR_ACCESS_DENIED` returned to the caller. |
| Logic Risk | A denied or failed device-setup boundary must not be projected as success. False `ERROR_SUCCESS` can hide catalog verification failure. False `CR_SUCCESS` after logging "service not implemented" can let an installer continue as if driver installation succeeded, leaving installer state inconsistent with host device state and hiding the sandbox denial. |
| Official Shape | `docs/plan/srev-172-setupapi-driver-install-status.md` records Microsoft `VerifyCatalogFile`, SetupAPI, CfgMgr32 `CONFIGRET`, and `CM_MapCrToWin32Err` references. `docs/plan/srev-172-setupapi-driver-install-status.schema.json` records the JSON Schema draft-07 local `SETUPAPI_DRIVER_INSTALL_STATUS` contract. |
| Fix | `Setup_VerifyCatalogFile` now returns `__sys_VerifyCatalogFile(CatalogFullPath)` directly. `Setup_CM_Add_Driver_PackageW` and `Setup_CM_Add_Driver_Package_ExW` now return `SETUP_CM_DRIVER_PACKAGE_BLOCKED_STATUS`, defined as `CR_ACCESS_DENIED`, after logging `SBIE2205`. No hook installation, dynamic export lookup, argument count, log message, or disabled setup/remove hook behavior changed. |
| Acceptance Gate | `docs/plan/check-srev-172.py` validates the draft-07 schema, official references, `ldr.c` hook registration, `setup.c` owner surface, catalog status passthrough, removal of catalog failure-to-success rewrite, CfgMgr32 blocked-status constant, both driver-package hooks returning `CR_ACCESS_DENIED`, and ledger fragment; `docs/plan/check-srev-172.sh` is the matrix wrapper. Runtime gate: Windows DLL build for `setup.c`; signed and unsigned catalog verification smoke proving verifier status is preserved; driver-package installer smoke proving `CM_Add_Driver_PackageW` and `CM_Add_Driver_Package_ExW` show `SBIE2205` and return a non-success `CONFIGRET`; compatibility observation for installers that previously advanced after false success. |
