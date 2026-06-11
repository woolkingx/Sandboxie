---
kind: srev-ledger-entry
id: SREV-115
title: My WinNT Warning Boundary
status: patched-source-level-after-official-msvc-warning-pragma-and-c4267-warning-shape-
owner: Sandboxie/core/drv/my_winnt.h
spec: docs/plan/srev-115-my-winnt-warning-boundary.md
schema: docs/plan/srev-115-my-winnt-warning-boundary.schema.json
checker: docs/plan/check-srev-115.py
runtime_gate: "Windows WDK build with normal warning level proving includer warning state is restored after `my_winnt.h`, x86/x64/ARM64 driver compile matrix, runtime smoke for consumers of `SYSTEM_PROCESS_INFORMATION`, `SYSTEM_MODULE_INFORMATION`, object-manager structures, and ALPC declarations, plus Driver Verifier / HVCI where supported"
---
### SREV-115: My WinNT Warning Boundary

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | patched source-level after official MSVC warning pragma and C4267 warning shape; needs Windows WDK build/runtime consumer proof |
| Evidence | `Sandboxie/core/drv/my_winnt.h` was the highest-ranked unnamed reviewable core file after SREV-114. The file is a driver-wide NT compatibility shim: it includes `ntifs.h` and `alpc.h`, then declares missing or private NT constants, prototypes, object-manager structures, system-information structures, and thread/process helpers used by many driver modules. The old header disabled MSVC warning C4267 at file scope without a matching restore. Microsoft documents C4267 as conversion from `size_t` to a smaller type, and documents `#pragma warning(push)` / `#pragma warning(pop)` as storing and restoring warning state, specifically useful for headers. |
| Data | `my_winnt.h`, include guard `_MY_WINNT_H`, `#pragma warning(disable : 4267)`, `#pragma warning(push)`, `#pragma warning(pop)`, `ntifs.h`, `alpc.h`, `OBJECT_TYPE`, `OBJECT_HEADER`, `SYSTEM_PROCESS_INFORMATION`, `SYSTEM_MODULE_INFORMATION`, `ZwQuerySystemInformation`, process/thread access masks, and private NT compatibility declarations. |
| Schema | `MY_WINNT_WARNING_BOUNDARY` says `my_winnt.h` is a driver-wide NT compatibility shim for declarations not supplied by every target WDK/DDK combination; private NT structure declarations are compatibility data shapes and not architecture truth by themselves; the header may suppress C4267 only for declarations inside the header; any warning-state mutation introduced by the header is restored before the include guard closes; the C4267 suppression does not cross into includer code; private NT structure layouts, function prototypes, access masks, object-manager structures, and system-information structures must not change in this SREV. |
| Topology | Driver source includes `driver.h` / `util.h`, which include `my_winnt.h`. The header includes WDK and local ALPC declarations, pushes MSVC warning state, suppresses C4267 only for the compatibility declarations in the guarded header body, declares private NT shapes, then pops warning state before the include guard closes. Downstream driver code resumes the includer's original warning state. |
| Logic Risk | Header-level warning mutations are global to the remainder of the including translation unit unless explicitly restored. Leaving C4267 disabled past this shim can hide 64-bit truncation mistakes in later driver code. The private NT declarations in this file are also high-risk, but they cannot be made correct by average-pattern cleanup; they require WDK/build/runtime layout validation. |
| Official Shape | `docs/plan/srev-115-my-winnt-warning-boundary.md` records Microsoft `#pragma warning` and compiler warning C4267 references. `docs/plan/srev-115-my-winnt-warning-boundary.schema.json` records the JSON Schema draft-07 local `MY_WINNT_WARNING_BOUNDARY` contract. |
| Fix | `my_winnt.h` now wraps the C4267 suppression with `#pragma warning(push)` and `#pragma warning(pop)`. No NT declarations, prototypes, access masks, structure layouts, include order, or consumers changed. |
| Acceptance Gate | `docs/plan/check-srev-115.py` validates the draft-07 schema, official references, header warning push/disable/pop order, one push and one pop, preservation of key private NT declaration nodes, and ledger entry; `docs/plan/check-srev-115.sh` is the matrix wrapper. Runtime/build gate: Windows WDK build with normal warning level proving includer warning state is restored after `my_winnt.h`, x86/x64/ARM64 driver compile matrix, runtime smoke for consumers of `SYSTEM_PROCESS_INFORMATION`, `SYSTEM_MODULE_INFORMATION`, object-manager structures, and ALPC declarations, plus Driver Verifier / HVCI where supported. |
