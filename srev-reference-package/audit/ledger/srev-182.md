---
kind: srev-ledger-entry
id: SREV-182
title: Driver Hook Header Guard Boundary
status: patched-source-level-after-official-cpp-include-guard-review-needs-windows-driver-build-proof
owner: Sandboxie/core/drv/hook.h
spec: docs/plan/srev-182-driver-hook-header-guard-boundary.md
schema: docs/plan/srev-182-driver-hook-header-guard-boundary.schema.json
checker: docs/plan/check-srev-182.py
runtime_gate: "Windows driver build proving hook-related driver translation units still compile and hook lookup smoke proving service index and Zw/Nt service resolution behavior is unchanged"
---
### SREV-182: Driver Hook Header Guard Boundary

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | patched source-level after official C++ include-guard review; needs Windows driver build proof |
| Evidence | `Sandboxie/core/drv/hook.h` was the highest-ranked unnamed reviewable core file after SREV-181. It includes `Sandboxie/core/dll/hook.h` for shared hook/trampoline declarations, then declares driver-owned APIs such as `Hook_GetService`, `Hook_GetNtServiceInternal`, `Hook_GetZwServiceInternal`, and `Hook_Api_Tramp`. Before this SREV, driver `hook.h` used `_MY_HOOK_H`, the same guard owned and defined by DLL `hook.h`, and relied on the DLL include side effect to protect the driver header. |
| Data | `Sandboxie/core/drv/hook.h`, `Sandboxie/core/dll/hook.h`, `_MY_HOOK_H`, `_MY_DRV_HOOK_H`, `HOOK_WITH_PRIVATE_PARTS`, `HOOK_TRAMP`, `HOOK_INST`, `Hook_BuildTramp`, `Hook_Analyze`, `Hook_GetService`, `Hook_GetNtServiceInternal`, `Hook_GetZwServiceInternal`, `Hook_Api_Tramp`, `hook.c`, `hook_32.c`, and `hook_64.c`. |
| Schema | `DRIVER_HOOK_HEADER_GUARD_BOUNDARY` says `drv/hook.h` owns driver-side hook declarations; `dll/hook.h` owns shared trampoline and instruction-analysis declarations; `drv/hook.h` has a driver-owned include guard independent from `dll/hook.h`; `drv/hook.h` may include `dll/hook.h` for shared types but must not rely on `dll/hook.h` to define the driver guard; including `dll/hook.h` before `drv/hook.h` must not suppress driver-only prototypes; driver-only prototypes remain `Hook_GetService`, `Hook_GetNtServiceInternal`, `Hook_GetZwServiceInternal`, and `Hook_Api_Tramp`; this SREV does not change hook implementation, syscall service lookup, trampoline layout, or instruction decoding. |
| Topology | Legal header topology is driver translation unit -> `#include "hook.h"` -> `_MY_DRV_HOOK_H` protects driver declarations -> include `../dll/hook.h` -> `_MY_HOOK_H` protects shared declarations -> expose driver-owned service/tramp API. DLL `hook.h` owns shared `HOOK_TRAMP` / `HOOK_INST` / `Hook_BuildTramp` / `Hook_Analyze`; driver `hook.h` owns service lookup and API trampoline declarations. |
| Logic Risk | The old shape made driver declarations depend on a guard macro owned by another header. If a future driver source or generated unity build included `../dll/hook.h` first, `_MY_HOOK_H` would already be defined and a later include of `drv/hook.h` would skip the driver-only prototypes. Include order should not decide whether driver APIs are declared. |
| Official Shape | `docs/plan/srev-182-driver-hook-header-guard-boundary.md` records Microsoft C++ header-file and include-guard documentation. `docs/plan/srev-182-driver-hook-header-guard-boundary.schema.json` records the JSON Schema draft-07 local `DRIVER_HOOK_HEADER_GUARD_BOUNDARY` contract. |
| Fix | `drv/hook.h` now uses `_MY_DRV_HOOK_H` as its own guard while still including `../dll/hook.h` for shared hook declarations. No hook implementation, syscall service lookup, trampoline layout, instruction decoder, `HOOK_WITH_PRIVATE_PARTS`, or source include list changed. |
| Acceptance Gate | `docs/plan/check-srev-182.py` validates the draft-07 schema, official references, driver-owned guard, DLL-owned guard preservation, driver-only prototype exposure after the DLL include, removal of the stale shared guard dependency, source include evidence, and ledger fragment; `docs/plan/check-srev-182.sh` is the matrix wrapper. Runtime gate: Windows driver build proving `hook.c`, `hook_32.c`, `hook_64.c`, `driver.c`, `api.c`, `process.c`, `gui_xp.c`, `process_hook.c`, and `key.c` still compile with the driver header; hook lookup smoke proving service index and Zw/Nt service resolution behavior is unchanged. |
