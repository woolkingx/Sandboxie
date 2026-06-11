# SREV-172: SetupAPI Driver Install Status

## Stage Gate

```text
stage: schema -> boundary -> topology -> logic -> action -> verify
input artifact: Sandboxie/core/dll/setup.c, ldr.c setup/cfgmgr hook registration, Microsoft VerifyCatalogFile and CfgMgr32 CONFIGRET documentation
output artifact: device setup hooks preserve failure status instead of projecting blocked driver install or catalog verification failure as success
owner: Sandboxie/core/dll/setup.c
acceptance gate: docs/plan/check-srev-172.py and docs/plan/check-srev-172.sh
```

## Data

`setup.c` owns Sandboxie DLL hooks for selected setup and Configuration Manager
entry points:

- `Setup_Init_SetupApi` hooks `setupapi!VerifyCatalogFile`.
- `Setup_VerifyCatalogFile` mediates catalog verification results.
- `Setup_Init_CfgMgr32` hooks `cfgmgr32!CM_Add_Driver_PackageW` and
  `cfgmgr32!CM_Add_Driver_Package_ExW` when those exports exist.
- The two `CM_Add_Driver_Package*` hooks log `SBIE2205` because driver package
  installation is not implemented inside the sandbox.

Before this SREV, two blocked/failure edges were projected as success:

- `Setup_VerifyCatalogFile` converted most nonzero verification failures into
  `ERROR_SUCCESS`.
- `Setup_CM_Add_Driver_PackageW` and `Setup_CM_Add_Driver_Package_ExW` logged
  "not implemented" but returned `0`, which is `CR_SUCCESS` in the CfgMgr32
  return-code shape.

## Official Shape

- Microsoft documents `VerifyCatalogFile` as unsupported and dynamically linked,
  but still defines its return contract: success returns `ERROR_SUCCESS`; for an
  Authenticode-signed catalog, trusted publisher success returns
  `ERROR_AUTHENTICODE_TRUSTED_PUBLISHER`; otherwise it returns verification
  errors such as `ERROR_AUTHENTICODE_TRUST_NOT_ESTABLISHED` or
  `ERROR_UNIDENTIFIED_ERROR`:
  `https://learn.microsoft.com/en-us/windows/win32/devnotes/verifycatalogfile`.
- Microsoft documents SetupAPI as the component used by device installation
  software for class installers, co-installers, and device installation
  applications:
  `https://learn.microsoft.com/en-my/windows-hardware/drivers/install/setupapi`.
- Microsoft CfgMgr32 documentation uses `CONFIGRET` return values where
  successful operations return `CR_SUCCESS` and failures return `CR_`-prefixed
  error codes defined in `Cfgmgr32.h`:
  `https://learn.microsoft.com/en-us/windows/win32/api/cfgmgr32/nf-cfgmgr32-cm_get_device_interface_listw`.
- Microsoft documents `CM_MapCrToWin32Err` as converting a `CONFIGRET` code to
  a Win32 error, proving that callers can interpret non-success `CR_` results
  as real failure status:
  `https://learn.microsoft.com/en-us/windows/win32/api/cfgmgr32/nf-cfgmgr32-cm_mapcrtowin32err`.

`CM_Add_Driver_PackageW` and `CM_Add_Driver_Package_ExW` are exported
CfgMgr32 functions but are not covered by a public Microsoft Learn function page
in this pass. This SREV therefore does not attempt to document their parameter
ABI beyond the existing local `ULONG_PTR` pass-through shape. It only fixes the
return-status projection for the locally blocked operation.

## Schema

`SETUPAPI_DRIVER_INSTALL_STATUS` says:

- `setup.c` owns the Sandboxie DLL hooks for SetupAPI catalog verification and
  CfgMgr32 driver-package addition.
- `VerifyCatalogFile` result values are owned by the original SetupAPI function;
  the hook may observe them but must not turn verification failure into
  `ERROR_SUCCESS`.
- `CM_Add_Driver_PackageW` and `CM_Add_Driver_Package_ExW` are driver package
  installation edges that Sandboxie intentionally blocks/logs.
- A blocked driver-package install must return a non-success `CONFIGRET`, not
  `CR_SUCCESS`.
- `CR_ACCESS_DENIED` is the local blocked status for these driver-package hooks.
- This SREV does not change hook installation, message id `2205`, function
  pointer parameter count, dynamic export lookup, or the disabled setup/remove
  hooks.
- Linux source gates are not Windows installer compatibility proof.

## Topology

Legal status topology after this SREV:

```text
setupapi.dll load
  -> Setup_Init_SetupApi
  -> hook VerifyCatalogFile
  -> Setup_VerifyCatalogFile
  -> original VerifyCatalogFile status returned unchanged

cfgmgr32.dll load
  -> Setup_Init_CfgMgr32
  -> optional hook CM_Add_Driver_PackageW / CM_Add_Driver_Package_ExW
  -> attempted driver package install
  -> SBIE2205 warning
  -> CR_ACCESS_DENIED
```

This keeps the sandbox boundary honest: unimplemented driver installation is a
denied operation, not a successful install.

## Logic Risk

False success is dangerous at this boundary. A device installer that receives
`ERROR_SUCCESS` from a failed catalog verification or `CR_SUCCESS` from a
blocked driver-package add can continue as if trust verification or driver
installation happened. That hides a denied host-impacting operation behind a
green status and makes later installer state inconsistent with the host device
state.

The correct minimal repair is not to implement driver installation inside the
sandbox. The correct repair is to preserve the official status shape: catalog
verification returns the real verifier status, and blocked CfgMgr32 driver
package addition returns an explicit non-success code.

## Action

`Setup_VerifyCatalogFile` now returns `__sys_VerifyCatalogFile` directly.

`Setup_CM_Add_Driver_PackageW` and `Setup_CM_Add_Driver_Package_ExW` now return
`SETUP_CM_DRIVER_PACKAGE_BLOCKED_STATUS`, defined as `CR_ACCESS_DENIED`, after
logging `SBIE2205`.

## Verification

Source-level gates:

```bash
python3 docs/plan/check-srev-172.py
bash docs/plan/check-srev-172.sh
python3 docs/plan/check-core-coverage.py
```

Full closure matrix:

```bash
python3 docs/plan/check-srev-172.py &&
bash docs/plan/check-srev-172.sh &&
python3 docs/plan/check-core-coverage.py &&
for s in docs/plan/check-srev-0*.sh docs/plan/check-srev-1*.sh docs/plan/check-kpath-0*.sh; do bash "$s"; done &&
git diff --check
```

Runtime/build gate: Windows DLL build for `setup.c`; signed and unsigned
catalog verification smoke proving verifier status is preserved; driver-package
installer smoke proving `CM_Add_Driver_PackageW` and
`CM_Add_Driver_Package_ExW` show `SBIE2205` and return a non-success
`CONFIGRET`; compatibility observation for installers that previously advanced
after false success.
