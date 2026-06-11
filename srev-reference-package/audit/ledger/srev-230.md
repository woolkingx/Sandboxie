---
kind: srev-ledger-entry
id: SREV-230
title: Service PCH Boundary Contract
status: docs-only-source-topology-reviewed-needs-windows-service-build-proof
owner: Sandboxie/core/svc/stdafx.h
additional_owners:
  - Sandboxie/core/svc/stdafx.cpp
spec: docs/plan/srev-230-service-pch-boundary-contract.md
schema: docs/plan/srev-230-service-pch-boundary-contract.schema.json
checker: docs/plan/check-srev-230.py
runtime_gate: Windows SboxSvc build for supported configurations proves that the PCH use/create topology and service compile environment still compile.
---

### SREV-230: Service PCH Boundary Contract

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | docs-only source topology reviewed; needs Windows service build proof |
| Evidence | `Sandboxie/core/svc/stdafx.h` was the top unnamed reviewable core file after SREV-229, and `Sandboxie/core/svc/stdafx.cpp` was still in the unnamed queue. Source readback shows these files own the service precompiled-header boundary. `stdafx.h` defines `_HAS_EXCEPTIONS 0`, includes `<ntstatus.h>` before `WIN32_NO_STATUS`, defines local `NTSTATUS`, defines `VC_EXTRALEAN`, includes `<windows.h>`, `common/defines.h`, and `core/dll/sbiedll.h`. `stdafx.cpp` includes only `stdafx.h`. `SboxSvc.vcxproj` uses PCH for service translation units and creates it from `stdafx.cpp`. |
| Data | `stdafx.h`, `stdafx.cpp`, `SboxSvc.vcxproj`, `_HAS_EXCEPTIONS`, `WIN32_NO_STATUS`, `NTSTATUS`, `VC_EXTRALEAN`, `<windows.h>`, `common/defines.h`, `core/dll/sbiedll.h`, `PrecompiledHeader Use`, and `PrecompiledHeader Create`. |
| Schema | `SERVICE_PCH_BOUNDARY_CONTRACT` says `stdafx.h` owns the service compile environment shared by translation units that use the service PCH; `stdafx.cpp` owns PCH creation by including only `stdafx.h`; `SboxSvc.vcxproj` owns the build topology that uses the PCH for normal service translation units and creates it from `stdafx.cpp`; `_HAS_EXCEPTIONS 0` is a compile contract; `WIN32_NO_STATUS` and local `NTSTATUS` are header-order contracts; runtime defects belong to the concrete service owner that performs the transition, not to `stdafx.h` or `stdafx.cpp` without a proven compile-boundary defect. |
| Topology | `SboxSvc.vcxproj -> ClCompile PrecompiledHeader=Use for service translation units -> stdafx.cpp PrecompiledHeader=Create -> #include "stdafx.h" -> service compile environment -> concrete service .cpp owners`. |
| Logic Risk | The coverage score is high because `stdafx.h` includes Windows and Sandboxie headers, and because `stdafx.cpp` participates in the MSVC build. Treating that score as a runtime defect would create false ownership. The right review action is to record the compile boundary and keep runtime findings attached to the service file that owns the behavior. |
| Official Shape | No new Windows/API runtime behavior is defined by these files. This SREV is a local MSVC/service compile-topology classification. Windows build proof remains required because Linux source checks cannot prove precompiled-header behavior. |
| Fix | No source patch. This SREV records `stdafx.h` and `stdafx.cpp` as service PCH/build-boundary files and closes them as docs-only coverage. Future changes to these files must prove a compile-environment or include-order defect. |
| Acceptance Gate | `docs/plan/check-srev-230.py` validates the draft-07 schema, `stdafx.h` compile environment, `stdafx.cpp` PCH creator shape, `SboxSvc.vcxproj` `PrecompiledHeader` use/create topology, split ledger fragment, and absence of runtime owner claims; `docs/plan/check-srev-230.sh` is the targeted wrapper. Runtime/build gate: Windows `SboxSvc` build for supported configurations proves that the PCH use/create topology and service compile environment still compile. |
