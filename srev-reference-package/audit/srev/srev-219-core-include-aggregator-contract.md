# SREV-219: Core Include Aggregator Contract

## Stage

data -> schema -> boundary -> topology -> logic -> verify

## Evidence

After SREV-218, the top unnamed reviewable files were
`Sandboxie/core/drv/includes.c`, `Sandboxie/core/svc/includes.cpp`, and
`Sandboxie/core/dll/includes.c`. These files are compile-time aggregation
translation units: they include shared `common/*.c` implementations into the
driver, service, and DLL targets with target-specific macros and headers.

The coverage score is high because included common modules carry NT, COM, map,
pool, stream, pattern, and firewall-related terms. The aggregator files
themselves do not own runtime policy, IPC decisions, Windows API calls, or
service/driver request transitions.

## Data

`includes.c`, `includes.cpp`, `SboxDrv.vcxproj`, `SboxSvc.vcxproj`,
`SboxDll.vcxproj`, `common/list.c`, `common/pool.c`, `common/map.c`,
`common/stream.c`, `common/pattern.c`, `common/str_util.c`, `common/netfw.c`,
`common/crc.c`, `common/rc4.c`, and `common/verify.c`.

## Schema

`CORE_INCLUDE_AGGREGATOR_CONTRACT` says:

- Driver `includes.c` is a compile translation unit for shared common C modules
  under `KERNEL_MODE` and driver pool-tag/memory macro shape.
- DLL `includes.c` is a compile translation unit for shared common C modules
  under DLL headers and Win32/NT compatibility headers.
- Service `includes.cpp` is a compile translation unit for shared common C
  modules under service `stdafx.h`, `extern "C"`, and service pool-tag shape.
- The aggregator files may set target-local macros before including common
  modules.
- Runtime defects in an included common module belong to the included module
  and the target macro shape that changes it, not to a blind source patch in
  the aggregator.
- A future change to an aggregator must prove the target-specific macro,
  linkage, and included-module topology before behavior claims.

## Topology

```text
SboxDrv.vcxproj -> Sandboxie/core/drv/includes.c
  -> KERNEL_MODE / driver pool macro shape
  -> common/list.c, pool.c, stream.c, pattern.c, map.c, netfw.c, str_util.c

SboxDll.vcxproj -> Sandboxie/core/dll/includes.c
  -> dll.h / windows.h / win32_ntddk.h
  -> common/list.c, pool.c, map.c, stream.c, netfw.c, str_util.c

SboxSvc.vcxproj -> Sandboxie/core/svc/includes.cpp
  -> stdafx.h / win32_ntddk.h / extern "C"
  -> common/list.c, pool.c, map.c, crc.c, rc4.c, pattern.c, stream.c,
     str_util.c, verify.c
```

## Logic Risk

Treating these files as runtime owners would create false ownership. The same
shared module can be compiled under different target macros; therefore the
correct review unit is either:

- the included common module itself; or
- the target-specific macro/linkage shape that changes how that common module
  behaves.

The include aggregator is still important because it names compile topology,
but it should not receive behavior patches just to satisfy coverage.

## Fix

No source patch. This SREV records the compile topology and closes the three
aggregator files as docs-only coverage. Future source changes should target the
included common module or a proven target macro/linkage defect.

## Acceptance Gate

`docs/plan/check-srev-219.py` validates the draft-07 schema, project-file
`ClCompile` ownership, include topology for driver/DLL/service aggregators,
target-local macros and linkage gates, split ledger fragment, and absence of
runtime API/IPC ownership claims in this SREV.

Runtime/build gate: Windows build for `SboxDrv`, `SboxDll`, and `SboxSvc`
continues to compile the aggregator translation units with the same included
common modules. Linux source checks cannot prove MSVC/WDK compile behavior.
