---
kind: srev-ledger-entry
id: SREV-219
title: Core Include Aggregator Contract
status: docs-only-source-topology-reviewed-needs-windows-build-proof
owner: Sandboxie/core/drv/includes.c
additional_owners:
  - Sandboxie/core/dll/includes.c
  - Sandboxie/core/svc/includes.cpp
spec: docs/plan/srev-219-core-include-aggregator-contract.md
schema: docs/plan/srev-219-core-include-aggregator-contract.schema.json
checker: docs/plan/check-srev-219.py
runtime_gate: Windows build for SboxDrv, SboxDll, and SboxSvc continues to compile the aggregator translation units with the same included common modules. Linux source checks cannot prove MSVC or WDK compile behavior.
---

### SREV-219: Core Include Aggregator Contract

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | docs-only source topology reviewed; needs Windows build proof |
| Evidence | After SREV-218, `Sandboxie/core/drv/includes.c`, `Sandboxie/core/svc/includes.cpp`, and `Sandboxie/core/dll/includes.c` were the top unnamed reviewable files. Source readback shows they are compile-time aggregation translation units that include shared `common/*.c` modules into the driver, service, and DLL targets. `SboxDrv.vcxproj`, `SboxSvc.vcxproj`, and `SboxDll.vcxproj` each compile the corresponding aggregator file directly. |
| Data | `includes.c`, `includes.cpp`, `SboxDrv.vcxproj`, `SboxSvc.vcxproj`, `SboxDll.vcxproj`, `common/list.c`, `common/pool.c`, `common/map.c`, `common/stream.c`, `common/pattern.c`, `common/str_util.c`, `common/netfw.c`, `common/crc.c`, `common/rc4.c`, and `common/verify.c`. |
| Schema | `CORE_INCLUDE_AGGREGATOR_CONTRACT` says driver `includes.c` is a compile translation unit for shared common C modules under `KERNEL_MODE` and driver pool-tag or memory macro shape; DLL `includes.c` is a compile translation unit under DLL headers and Win32/NT compatibility headers; service `includes.cpp` is a compile translation unit under service `stdafx.h`, `extern "C"`, and service pool-tag shape; aggregators may set target-local macros before including common modules; runtime defects in an included common module belong to the included module and target macro shape that changes it; and future aggregator changes must prove target-specific macro, linkage, and included-module topology before behavior claims. |
| Topology | `SboxDrv.vcxproj -> drv/includes.c -> KERNEL_MODE / driver pool macro shape -> common/list.c, pool.c, stream.c, pattern.c, map.c, netfw.c, str_util.c`. `SboxDll.vcxproj -> dll/includes.c -> dll.h / windows.h / win32_ntddk.h -> common/list.c, pool.c, map.c, stream.c, netfw.c, str_util.c`. `SboxSvc.vcxproj -> svc/includes.cpp -> stdafx.h / win32_ntddk.h / extern "C" -> common/list.c, pool.c, map.c, crc.c, rc4.c, pattern.c, stream.c, str_util.c, verify.c`. |
| Logic Risk | Treating these files as runtime owners would create false ownership. The same shared module can be compiled under different target macros, so the correct review unit is either the included common module itself or the target-specific macro/linkage shape that changes how that common module behaves. |
| Official Shape | No Windows/API-facing behavior is defined by these aggregator files. This is a local compile-topology SREV, so official Microsoft API references are not required for the docs-only closure. |
| Fix | No source patch. This SREV records the compile topology and closes the three aggregator files as docs-only coverage. Future source changes should target the included common module or a proven target macro/linkage defect. |
| Acceptance Gate | `docs/plan/check-srev-219.py` validates the draft-07 schema, project-file `ClCompile` ownership, include topology for driver/DLL/service aggregators, target-local macros and linkage gates, split ledger fragment, and absence of runtime API/IPC ownership claims in this SREV; `docs/plan/check-srev-219.sh` is the targeted wrapper. Runtime/build gate: Windows build for `SboxDrv`, `SboxDll`, and `SboxSvc` continues to compile the aggregator translation units with the same included common modules. Linux source checks cannot prove MSVC/WDK compile behavior. |
