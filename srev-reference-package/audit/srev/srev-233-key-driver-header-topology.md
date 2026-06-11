# SREV-233: Key Driver Header Topology Contract

## Stage

data -> schema -> boundary -> topology -> logic -> verify

## Evidence

After SREV-232, `Sandboxie/core/drv/key.h` was the top unnamed reviewable core
file. Source readback shows it is the declaration header for the driver registry
module. It includes `driver.h` and exposes five module entry points:
`Key_Init`, `Key_Unload`, `Key_MountHive`, `Key_UnmountHive`, and
`Key_InitProcess`.

The runtime owners are elsewhere:

- `Sandboxie/core/drv/key.c` owns the shared registry path policy,
  `Key_Mounts` state, hive mount/unmount lifecycle, API handler registration,
  and the common `Key_MyParseProc_2` allow/deny decision.
- `Sandboxie/core/drv/key_flt.c` owns the Vista-and-later registry callback
  registration and `REG_NOTIFY_CLASS` pre-operation routing.
- `Sandboxie/core/drv/key_xp.c` owns the legacy 32-bit XP parse-procedure hook
  and hotfix-dependent parse-context detection.
- `Sandboxie/core/drv/driver.c` owns driver module initialization order and
  calls `Key_Init`.
- `Sandboxie/core/drv/process.c` owns process lifecycle sequencing and calls
  `Key_MountHive`, `Key_InitProcess`, and `Key_UnmountHive`.

Several registry behavior risks already have specific SREV owners, including
SREV-047 for low-label boxed registry paths, SREV-098 for the IE embedding
registry policy, SREV-167 for the XP hotfix probe kernel-handle boundary,
SREV-176 for key utility registry path shape, and SREV-227 for counted driver
registry path copy.

## Data

`Key_Init`, `Key_Unload`, `Key_MountHive`, `Key_UnmountHive`,
`Key_InitProcess`, `PROCESS`, `Key_Mounts`, `Key_MyParseProc_2`,
`Key_Init_Filter`, `Key_Unload_Filter`, `Key_Callback`, `Key_Init_XpHook`,
`Key_Unload_XpHook`, `Key_MyParseProc`, `driver.c`, and `process.c`.

## Schema

`KEY_DRIVER_HEADER_TOPOLOGY_CONTRACT` says:

- `key.h` is the driver registry module declaration header.
- The header may include `driver.h` and declare module lifecycle/process entry
  points that take or return local driver types.
- The header must not be treated as the owner of registry filter registration,
  parse-hook behavior, registry path allow/deny policy, hive load/unload
  sequencing, app-hive handling, service API handlers, or key mount state.
- Runtime behavior changes belong to `key.c`, `key_flt.c`, `key_xp.c`,
  `driver.c`, or `process.c`, depending on the transition.
- Future changes to this header must prove driver initialization and process
  lifecycle topology before making behavior claims.

## Topology

```text
DriverEntry / driver initialization
-> Driver_Init
-> Key_Init
-> Vista+ Key_Init_Filter / XP Key_Init_XpHook
-> registry callback or parse hook
-> Key_MyParseProc_2 registry path decision

process image initialization
-> Process_NotifyImage
-> File_CreateBoxPath / Ipc_CreateBoxPath
-> Key_MountHive
-> Key_InitProcess
-> registry path lists become active for the process

process delete
-> Process_Delete
-> Key_UnmountHive
-> SbieSvc unmount request if this was the last mount user
```

The header is the declaration node in this topology. It is not the owner of the
policy transition, callback ABI, object handle rules, or hive mount transaction.

## Logic Risk

The high coverage score comes from `key.h` naming boundary-heavy entry points:
registry callbacks, NT object paths, sandbox hive mounting, and process
lifecycle wiring. Treating the header as a runtime owner would create false
ownership and encourage edits in a file that cannot enforce registry semantics.
The correct next behavior reviews must target the concrete owner that executes
the crossing.

## Official Shape

Microsoft documents registry filtering as a kernel-mode callback surface. Vista
and later drivers use `CmRegisterCallbackEx`, the configuration manager invokes
the registered callback for registry operations, and registry filter drivers can
receive pre-operation notifications. Microsoft also documents application hives
under `\REGISTRY\A`, including the warning that filter drivers handling create
or open notifications must not use absolute `\REGISTRY\A\...` paths to open an
application hive.

The underlying registry-object and handle rules are the same official shapes
recorded by earlier registry SREVs: registry key objects are opened with
`OBJECT_ATTRIBUTES` plus `ZwOpenKey` or `ZwCreateKey`; private driver handles
must use `OBJ_KERNEL_HANDLE` when the driver is not running in a system thread
context.

## Fix

No source patch. This SREV records `key.h` as a declaration/topology header and
closes it as docs-only coverage. Future behavior patches should target the
owner that executes the relevant registry callback, parse hook, API handler,
hive mount, or process lifecycle transition.

## Acceptance Gate

`docs/plan/check-srev-233.py` validates the draft-07 schema, header declaration
shape, source owner topology in `key.c`, registry filter topology in
`key_flt.c`, XP parse-hook topology in `key_xp.c`, process/driver lifecycle
callers, existing registry SREV owner coverage, split ledger fragment, and
absence of runtime owner claims for this header.

Runtime/build gate: Windows driver build continues to compile `key.h` and the
registry module lifecycle still initializes through `driver.c`; registry runtime
behavior remains covered by the existing and future concrete-owner SREV Windows
gates.
