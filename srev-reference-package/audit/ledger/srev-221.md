---
kind: srev-ledger-entry
id: SREV-221
title: Core Resource Topology
status: patched-comment-topology-after-official-resource-and-versioninfo-review-needs-windows-resource-build-proof
owner: Sandboxie/core/dll/lowlevel.rc
additional_owners:
  - Sandboxie/core/dll/resource.rc
  - Sandboxie/core/drv/resource.rc
  - Sandboxie/core/svc/resource.rc
  - Sandboxie/core/svc/resource2.h
consumer: Sandboxie/core/dll/lowlevel_inject.c
spec: docs/plan/srev-221-core-resource-topology.md
schema: docs/plan/srev-221-core-resource-topology.schema.json
checker: docs/plan/check-srev-221.py
runtime_gate: Windows build must prove SbieDll contains LOWLEVEL32 and LOWLEVEL64 resources for the relevant platform, and LowLevel injection still loads the matching embedded resource.
---

### SREV-221: Core Resource Topology

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | patched comment topology after official resource and VERSIONINFO review; needs Windows resource build proof |
| Evidence | `Sandboxie/core/dll/lowlevel.rc` is compiled by `Sandboxie/core/dll/SboxDll.vcxproj` into SbieDll and defines `LOWLEVEL32` / `LOWLEVEL64` RCDATA resources. `Sandboxie/core/dll/lowlevel_inject.c` reads those resources from `Dll_Instance` with `FindResource`, `SizeofResource`, `LoadResource`, and `LockResource`. Before this SREV, both comments claimed the resource was embedded in `SbieSvc`, but the current project file and loader prove SbieDll is the owner. The adjacent driver/DLL/service `resource.rc` files are `VS_VERSION_INFO` metadata files, and `Sandboxie/core/svc/resource2.h` is a legacy LowLevel RCDATA stub not compiled by the current service project. |
| Data | `lowlevel.rc`, `lowlevel_inject.c`, `LOWLEVEL32`, `LOWLEVEL64`, `RT_RCDATA`, `Dll_Instance`, `FindResource`, `SizeofResource`, `LoadResource`, `LockResource`, `SboxDll.vcxproj`, `resource.rc`, `VS_VERSION_INFO`, `FileDescription`, `OriginalFilename`, and `resource2.h`. |
| Schema | `CORE_RESOURCE_TOPOLOGY` says `lowlevel.rc` is compiled into SbieDll by `SboxDll.vcxproj`; `lowlevel.rc` owns `LOWLEVEL32` and `LOWLEVEL64` RCDATA resource names consumed by `lowlevel_inject.c`; `lowlevel_inject.c` must describe the resource as embedded in SbieDll because it looks up the resource from `Dll_Instance`; driver/DLL/service `resource.rc` files own `VERSIONINFO` metadata, not runtime policy; `svc/resource2.h` is not compiled by the current service project and is not the active LowLevel embedding surface; and runtime defects belong to the resource consumer or project build topology, not version metadata strings. |
| Topology | `SboxDll.vcxproj -> ResourceCompile lowlevel.rc -> LOWLEVEL32 / LOWLEVEL64 RT_RCDATA -> linked into SbieDll -> Dll_Instance -> lowlevel_inject.c FindResource/SizeofResource/LoadResource/LockResource -> LowLevel image parser/injector`. Version metadata topology is `SboxDrv.vcxproj -> drv/resource.rc -> VERSIONINFO for SbieDrv.sys`, `SboxDll.vcxproj -> dll/resource.rc -> VERSIONINFO for SbieDll.dll`, and `SboxSvc.vcxproj -> svc/resource.rc -> VERSIONINFO for SbieSvc.exe`. |
| Logic Risk | `FindResource` is module-scoped. Saying "SbieSvc" while the lookup runs against `Dll_Instance` hides the real owner and can make future resource or build fixes land in the wrong target. |
| Official Shape | `docs/plan/srev-221-core-resource-topology.md` records Microsoft resource lookup and `VERSIONINFO` references. The lowlevel resource ownership is local project topology. |
| Fix | `lowlevel.rc` and `lowlevel_inject.c` comments now name SbieDll as the embedded resource owner. The old build-pass narrative was replaced with the current project/consumer topology: `SboxDll.vcxproj` compiles `lowlevel.rc`, and `lowlevel_inject.c` reads `LOWLEVEL32` / `LOWLEVEL64` from `Dll_Instance`. No resource names, resource paths, version metadata, project files, or injection logic changed. |
| Acceptance Gate | `docs/plan/check-srev-221.py` validates the draft-07 schema, official resource references, SboxDll project ownership for `lowlevel.rc`, `LOWLEVEL32/64` resources, `lowlevel_inject.c` module-scoped lookup through `Dll_Instance`, driver/DLL/service `VERSIONINFO` metadata shape, inactive `resource2.h` topology, corrected comments, and split ledger fragment; `docs/plan/check-srev-221.sh` is the targeted wrapper. Runtime/build gate: Windows build must prove SbieDll contains `LOWLEVEL32` and `LOWLEVEL64` resources for the relevant platform, and LowLevel injection still loads the matching embedded resource. Linux source checks cannot prove compiled resource contents. |
