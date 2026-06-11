# SREV-182: Driver Hook Header Guard Boundary

## Data

`Sandboxie/core/drv/hook.h` is the driver-side hook management header. It
includes the shared DLL hook header `Sandboxie/core/dll/hook.h` for common
trampoline and instruction-analysis declarations, then adds driver-owned
declarations such as `Hook_GetService`, `Hook_GetNtServiceInternal`,
`Hook_GetZwServiceInternal`, and `Hook_Api_Tramp`.

Before this SREV, the driver header used the same `_MY_HOOK_H` include guard
as `../dll/hook.h`, and the driver header intentionally did not define the
guard itself. The guard was set as a side effect of including the DLL header.

## Official Shape

Microsoft's C++ header-file documentation describes include guards as the
normal way to ensure a header is not inserted multiple times into one source
file. Microsoft's `#pragma once` documentation describes the include guard
idiom as using a preprocessor macro to prevent multiple inclusions of the
contents of the file and warns that include guard choices matter for header
inclusion behavior.

```text
https://learn.microsoft.com/en-us/cpp/cpp/header-files-cpp?view=msvc-170
https://learn.microsoft.com/en-us/cpp/preprocessor/once?view=msvc-170
```

## Schema

Local schema:

```text
docs/plan/srev-182-driver-hook-header-guard-boundary.schema.json
```

The driver hook header guard contract is:

```text
drv/hook.h owns driver-side hook declarations
dll/hook.h owns shared trampoline and instruction-analysis declarations
drv/hook.h must have a driver-owned include guard independent from dll/hook.h
drv/hook.h may include dll/hook.h for shared types but must not rely on dll/hook.h to define the driver guard
including dll/hook.h before drv/hook.h must not suppress driver-only prototypes
driver-only prototypes remain Hook_GetService, Hook_GetNtServiceInternal, Hook_GetZwServiceInternal, and Hook_Api_Tramp
this SREV does not change hook implementation, syscall service lookup, trampoline layout, or instruction decoding
```

## Topology

Legal header topology:

```text
driver translation unit
  -> #include "hook.h"
  -> _MY_DRV_HOOK_H protects driver-only declarations
  -> include ../dll/hook.h
       -> _MY_HOOK_H protects shared hook declarations
  -> expose driver-owned service/tramp API
```

This separates two owners:

```text
dll/hook.h -> shared HOOK_TRAMP / HOOK_INST / Hook_BuildTramp / Hook_Analyze declarations
drv/hook.h -> driver service lookup and API trampoline declarations
```

## Logic Risk

The old shape made driver declarations depend on a guard macro owned by another
header. If a future driver source or generated unity build included
`../dll/hook.h` first, `_MY_HOOK_H` would already be defined and a later include
of `drv/hook.h` would skip the driver-only prototypes. That is a header
topology bug: include order would decide whether driver APIs are declared.

## Fix

`drv/hook.h` now uses `_MY_DRV_HOOK_H` as its own guard. It still includes
`../dll/hook.h`, so the shared hook declarations remain owned by the DLL header.

No hook implementation, syscall service lookup, trampoline code layout,
instruction decoder, `HOOK_WITH_PRIVATE_PARTS`, or source include list changed.

## Acceptance Gate

`docs/plan/check-srev-182.py` validates the draft-07 schema, official
references, driver-owned guard, DLL-owned guard preservation, driver-only
prototype exposure after the DLL include, removal of the stale shared guard
dependency, source include evidence, and ledger fragment.
`docs/plan/check-srev-182.sh` is the matrix wrapper.

Runtime/build gate: Windows driver build proving `hook.c`, `hook_32.c`,
`hook_64.c`, `driver.c`, `api.c`, `process.c`, `gui_xp.c`, `process_hook.c`,
and `key.c` still compile with the driver header; hook lookup smoke proving
service index and Zw/Nt service resolution behavior is unchanged.
