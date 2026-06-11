---
kind: srev-ledger-entry
id: SREV-233
title: Key Driver Header Topology Contract
status: docs-only-source-topology-reviewed-needs-windows-driver-build-proof
owner: Sandboxie/core/drv/key.h
additional_owners:
  - Sandboxie/core/drv/key.c
  - Sandboxie/core/drv/key_flt.c
  - Sandboxie/core/drv/key_xp.c
  - Sandboxie/core/drv/driver.c
  - Sandboxie/core/drv/process.c
spec: docs/plan/srev-233-key-driver-header-topology.md
schema: docs/plan/srev-233-key-driver-header-topology.schema.json
checker: docs/plan/check-srev-233.py
runtime_gate: Windows driver build continues to compile key.h and the registry module lifecycle still initializes through driver.c; registry runtime behavior remains covered by existing and future concrete-owner SREV Windows gates.
---

### SREV-233: Key Driver Header Topology Contract

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | docs-only source topology reviewed; needs Windows driver build proof |
| Evidence | `Sandboxie/core/drv/key.h` was the top unnamed reviewable core file after SREV-232. Source readback shows it is the declaration header for the driver registry module. It includes `driver.h` and exposes five module entry points: `Key_Init`, `Key_Unload`, `Key_MountHive`, `Key_UnmountHive`, and `Key_InitProcess`. Runtime ownership lives in `key.c`, `key_flt.c`, `key_xp.c`, `driver.c`, and `process.c`. |
| Data | `Key_Init`, `Key_Unload`, `Key_MountHive`, `Key_UnmountHive`, `Key_InitProcess`, `PROCESS`, `Key_Mounts`, `Key_MyParseProc_2`, `Key_Init_Filter`, `Key_Unload_Filter`, `Key_Callback`, `Key_Init_XpHook`, `Key_Unload_XpHook`, `Key_MyParseProc`, `driver.c`, and `process.c`. |
| Schema | `KEY_DRIVER_HEADER_TOPOLOGY_CONTRACT` says `key.h` is the driver registry module declaration header; it may include `driver.h` and declare module lifecycle/process entry points that take or return local driver types; it does not own registry filter registration, parse-hook behavior, registry path allow/deny policy, hive load/unload sequencing, app-hive handling, service API handlers, or key mount state; runtime behavior changes belong to the concrete owner that executes the transition; and future header changes must prove driver initialization and process lifecycle topology before behavior claims. |
| Topology | `DriverEntry / driver initialization -> Driver_Init -> Key_Init -> Vista+ Key_Init_Filter / XP Key_Init_XpHook -> registry callback or parse hook -> Key_MyParseProc_2 registry path decision`. Process flow is `Process_NotifyImage -> File_CreateBoxPath / Ipc_CreateBoxPath -> Key_MountHive -> Key_InitProcess -> registry path lists become active for the process`; teardown is `Process_Delete -> Key_UnmountHive -> SbieSvc unmount request if this was the last mount user`. |
| Logic Risk | The high coverage score comes from `key.h` naming boundary-heavy entry points: registry callbacks, NT object paths, sandbox hive mounting, and process lifecycle wiring. Treating the header as a runtime owner would create false ownership and encourage edits in a file that cannot enforce registry semantics. The correct next behavior reviews must target the concrete owner that executes the crossing. |
| Official Shape | Microsoft registry-filter documentation says registry callbacks are registered with `CmRegisterCallback` or `CmRegisterCallbackEx`; Vista and later drivers should use `CmRegisterCallbackEx`; callbacks can receive registry pre-operation notifications; application hives live under `\REGISTRY\A`; and registry filter drivers handling create/open notifications must not use absolute `\REGISTRY\A\...` paths to open an application hive. Microsoft registry-object documentation says registry key handles are opened with `OBJECT_ATTRIBUTES` plus `ZwOpenKey`/`ZwCreateKey`, and private driver handles must use `OBJ_KERNEL_HANDLE` when required by process context. |
| Fix | No source patch. This SREV records `key.h` as a declaration/topology header and closes it as docs-only coverage. Future behavior patches should target the owner that executes the relevant registry callback, parse hook, API handler, hive mount, or process lifecycle transition. |
| Acceptance Gate | `docs/plan/check-srev-233.py` validates the draft-07 schema, header declaration shape, source owner topology in `key.c`, registry filter topology in `key_flt.c`, XP parse-hook topology in `key_xp.c`, process/driver lifecycle callers, existing registry SREV owner coverage, split ledger fragment, and absence of runtime owner claims for this header; `docs/plan/check-srev-233.sh` is the targeted wrapper. Runtime/build gate: Windows driver build continues to compile `key.h` and the registry module lifecycle still initializes through `driver.c`; registry runtime behavior remains covered by the existing and future concrete-owner SREV Windows gates. |
