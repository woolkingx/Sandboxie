# SREV-230: Service PCH Boundary Contract

## Stage

data -> schema -> boundary -> topology -> logic -> verify

## Evidence

After SREV-229, `Sandboxie/core/svc/stdafx.h` was the top unnamed reviewable
core file, and `Sandboxie/core/svc/stdafx.cpp` was still in the unnamed queue.
Source readback shows these files own the service precompiled-header boundary,
not a runtime IPC, COM, RPC, file, registry, or driver policy transition.

`stdafx.h` defines the service compile environment: `_HAS_EXCEPTIONS 0`,
`<ntstatus.h>` before `WIN32_NO_STATUS`, a local `NTSTATUS` typedef, `VC_EXTRALEAN`,
`<windows.h>`, `common/defines.h`, and `core/dll/sbiedll.h`. `stdafx.cpp`
includes only `stdafx.h`, matching the MSVC precompiled-header creator role.
`SboxSvc.vcxproj` sets `PrecompiledHeader` to `Use` for service compile
configurations and sets `stdafx.cpp` to `Create`; it also lists `stdafx.h` as a
service include file.

## Data

`stdafx.h`, `stdafx.cpp`, `SboxSvc.vcxproj`, `_HAS_EXCEPTIONS`,
`WIN32_NO_STATUS`, `NTSTATUS`, `VC_EXTRALEAN`, `<windows.h>`,
`common/defines.h`, `core/dll/sbiedll.h`, `PrecompiledHeader Use`, and
`PrecompiledHeader Create`.

## Schema

`SERVICE_PCH_BOUNDARY_CONTRACT` says:

- `stdafx.h` owns the service compile environment shared by translation units
  that use the service PCH.
- `stdafx.cpp` owns PCH creation by including only `stdafx.h`.
- `SboxSvc.vcxproj` owns the build topology that uses the PCH for normal service
  translation units and creates it from `stdafx.cpp`.
- `_HAS_EXCEPTIONS 0` is a compile contract: code compiled under this header
  must not rely on C++ exception support.
- `WIN32_NO_STATUS` and the local `NTSTATUS` typedef are header-order contracts
  that keep Windows headers from redefining NT status symbols.
- Runtime defects belong to the concrete service owner that performs the
  transition, not to a source patch in `stdafx.h` or `stdafx.cpp` without a
  proven compile-boundary defect.

## Topology

```text
SboxSvc.vcxproj
-> ClCompile PrecompiledHeader=Use for service translation units
-> stdafx.cpp PrecompiledHeader=Create
-> #include "stdafx.h"
-> service compile environment
-> concrete service .cpp owners
```

The compile boundary is real, but it is not itself the runtime owner for COM,
RPC, PipeServer, driver API, file, registry, GUI, or token decisions.

## Logic Risk

The coverage score is high because `stdafx.h` includes Windows and Sandboxie
headers, and because `stdafx.cpp` participates in the MSVC build. Treating that
score as a runtime defect would create false ownership. The right review action
is to record the compile boundary and keep runtime findings attached to the
service file that owns the behavior.

## Official Shape

No new Windows/API runtime behavior is defined by these files. This SREV is a
local MSVC/service compile-topology classification. Windows build proof remains
required because Linux source checks cannot prove precompiled-header behavior.

## Fix

No source patch. This SREV records `stdafx.h` and `stdafx.cpp` as service
PCH/build-boundary files and closes them as docs-only coverage. Future changes
to these files must prove a compile-environment or include-order defect.

## Acceptance Gate

`docs/plan/check-srev-230.py` validates the draft-07 schema, `stdafx.h` compile
environment, `stdafx.cpp` PCH creator shape, `SboxSvc.vcxproj`
`PrecompiledHeader` use/create topology, split ledger fragment, and absence of runtime owner claims.

Runtime/build gate: Windows `SboxSvc` build for supported configurations proves
that the PCH use/create topology and service compile environment still compile.
