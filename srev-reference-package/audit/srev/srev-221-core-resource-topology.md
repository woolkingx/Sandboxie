# SREV-221: Core Resource Topology

## Stage

data -> schema -> boundary -> topology -> logic -> action -> verify

## Evidence

After SREV-220, `Sandboxie/core/dll/lowlevel.rc` was the top unnamed
reviewable core file. It is not runtime policy code. It is a resource
translation unit compiled by `Sandboxie/core/dll/SboxDll.vcxproj` into SbieDll.
It embeds `LowLevel.dll` artifacts as `LOWLEVEL32` and `LOWLEVEL64` RCDATA
resources.

`Sandboxie/core/dll/lowlevel_inject.c` reads these resources from
`Dll_Instance` with `FindResource`, `SizeofResource`, `LoadResource`, and
`LockResource`. Before this SREV, both `lowlevel.rc` and `lowlevel_inject.c`
claimed the resource was embedded in `SbieSvc`, but the current project file
and runtime loader prove the owner is SbieDll.

The adjacent `resource.rc` files for driver, DLL, and service are version-info
metadata files. `Sandboxie/core/svc/resource2.h` is a legacy LowLevel RCDATA
stub and is not compiled by the current service project.

## Data

`lowlevel.rc`, `lowlevel_inject.c`, `LOWLEVEL32`, `LOWLEVEL64`, `RT_RCDATA`,
`Dll_Instance`, `FindResource`, `SizeofResource`, `LoadResource`,
`LockResource`, `SboxDll.vcxproj`, `resource.rc`, `VS_VERSION_INFO`,
`FileDescription`, `OriginalFilename`, and `resource2.h`.

## Official Shape

Microsoft documents resource lookup as module-scoped: `FindResource` /
`FindResourceEx` locate a resource in a module and return a handle to the
resource data; `LoadResource` loads it; resource memory is tied to the loaded
module lifetime.

Microsoft documents `VERSIONINFO` as file metadata containing fields such as
version number, intended operating system, file description, and original
filename. The `resource.rc` files here are therefore metadata surfaces unless a
specific consumer reads one of those fields as behavior.

References:

- `https://learn.microsoft.com/en-us/windows/win32/menurc/finding-and-loading-resources`
- `https://learn.microsoft.com/en-us/windows/win32/menurc/versioninfo-resource`

## Schema

`CORE_RESOURCE_TOPOLOGY` says:

- `Sandboxie/core/dll/lowlevel.rc` is compiled into SbieDll by
  `SboxDll.vcxproj`.
- `lowlevel.rc` owns the `LOWLEVEL32` and `LOWLEVEL64` RCDATA resource names
  consumed by `lowlevel_inject.c`.
- `lowlevel_inject.c` must describe the resource as embedded in SbieDll because
  it looks up the resource from `Dll_Instance`.
- Driver, DLL, and service `resource.rc` files own `VERSIONINFO` metadata, not
  runtime policy.
- `Sandboxie/core/svc/resource2.h` is not compiled by the current service
  project and must not be treated as the active LowLevel embedding surface.
- Runtime behavior defects belong to the resource consumer or project build
  topology, not to version metadata strings.

## Topology

```text
SboxDll.vcxproj
-> ResourceCompile lowlevel.rc
-> LOWLEVEL32 / LOWLEVEL64 RT_RCDATA
-> linked into SbieDll
-> Dll_Instance
-> lowlevel_inject.c FindResource/SizeofResource/LoadResource/LockResource
-> LowLevel image parser/injector
```

Version metadata topology:

```text
SboxDrv.vcxproj -> drv/resource.rc -> VERSIONINFO for SbieDrv.sys
SboxDll.vcxproj -> dll/resource.rc -> VERSIONINFO for SbieDll.dll
SboxSvc.vcxproj -> svc/resource.rc -> VERSIONINFO for SbieSvc.exe
```

Legacy topology:

```text
svc/resource2.h
-> LOWLEVEL RCDATA declarations
-x current SboxSvc.vcxproj ResourceCompile list
```

## Logic Risk

The old comments named the wrong module owner. That is not a direct runtime bug,
but it is exactly the kind of topology drift that makes future resource or build
fixes land in the wrong target. Since `FindResource` is module-scoped, saying
"SbieSvc" while the lookup runs against `Dll_Instance` hides the real boundary:
SbieDll owns the embedded LowLevel payload used by the DLL injection path.

## Fix

`lowlevel.rc` and `lowlevel_inject.c` comments now name SbieDll as the embedded
resource owner. The old build-pass narrative was replaced with the current
project/consumer topology: `SboxDll.vcxproj` compiles `lowlevel.rc`, and
`lowlevel_inject.c` reads `LOWLEVEL32` / `LOWLEVEL64` from `Dll_Instance`.

No resource names, resource paths, version metadata, project files, or injection
logic changed.

## Acceptance Gate

`docs/plan/check-srev-221.py` validates the draft-07 schema, official resource
references, SboxDll project ownership for `lowlevel.rc`, `LOWLEVEL32/64`
resources, `lowlevel_inject.c` module-scoped lookup through `Dll_Instance`,
driver/DLL/service `VERSIONINFO` metadata shape, inactive `resource2.h`
topology, corrected comments, and split ledger fragment.

Runtime/build gate: Windows build must prove SbieDll contains `LOWLEVEL32` and
`LOWLEVEL64` resources for the relevant platform, and LowLevel injection still
loads the matching embedded resource. Linux source checks cannot prove compiled
resource contents.
