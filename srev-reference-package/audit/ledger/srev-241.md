---
kind: srev-ledger-entry
id: SREV-241
title: Taskbar Header Topology Contract
status: docs-only-source-topology-reviewed-needs-windows-dll-build-proof
owner: Sandboxie/core/dll/taskbar.h
additional_owners:
  - Sandboxie/core/dll/taskbar.c
  - Sandboxie/core/dll/sh.c
  - Sandboxie/core/dll/gui.c
  - Sandboxie/core/dll/guidlg.c
  - Sandboxie/core/dll/ldr.c
  - Sandboxie/core/dll/dll.h
  - docs/plan/ledger/srev-004.md
  - docs/plan/ledger/srev-228.md
spec: docs/plan/srev-241-taskbar-header-topology.md
schema: docs/plan/srev-241-taskbar-header-topology.schema.json
checker: docs/plan/check-srev-241.py
runtime_gate: Windows DLL build continues to compile taskbar.h and wire taskbar lifecycle through sh.c, ldr.c, gui.c, guidlg.c, and taskbar.c; runtime behavior remains covered by existing and future concrete-owner SREV Windows gates.
---

### SREV-241: Taskbar Header Topology Contract

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | docs-only source topology reviewed; needs Windows DLL build proof |
| Evidence | `Sandboxie/core/dll/taskbar.h` was the top unnamed reviewable core file after SREV-240. Source readback shows it is a small declaration header for shell taskbar integration. It declares `Taskbar_Init`, `Taskbar_SetProcessAppUserModelId`, and `Taskbar_SetWindowAppUserModelId`. The runtime owner is `taskbar.c`, which owns Shell/AppUserModelID hooks, `SHGetPropertyStoreForWindow` wrapping, AppUserModelID prefixing, taskbar property rewriting, and the local property-store COM wrapper. `sh.c` calls `Taskbar_Init`; `gui.c` and `guidlg.c` call the process/window AppUserModelID helpers. `Taskbar_SHCore_Init` is declared through `dll.h` for `ldr.c`, not through `taskbar.h`. |
| Data | `taskbar.h`, `taskbar.c`, `Taskbar_Init`, `Taskbar_SetProcessAppUserModelId`, `Taskbar_SetWindowAppUserModelId`, `Taskbar_SHCore_Init`, `sh.c`, `gui.c`, `guidlg.c`, `ldr.c`, `dll.h`, `SetCurrentProcessExplicitAppUserModelID`, `GetCurrentProcessExplicitAppUserModelID`, `SHGetPropertyStoreForWindow`, `IPropertyStore`, `PKEY_AppUserModel_ID`, `PKEY_AppUserModel_RelaunchCommand`, `PKEY_AppUserModel_RelaunchDisplayNameResource`, SREV-004, and SREV-228. |
| Schema | `TASKBAR_HEADER_TOPOLOGY_CONTRACT` says `taskbar.h` is the declaration header for shell taskbar entry points used by shell and GUI hook modules; `taskbar.c` owns the implementation, hook installation, AppUserModelID state, property-store wrapper, COM behavior, and Shell property rewriting; `sh.c`, `gui.c`, and `guidlg.c` are legal local callers for the functions declared by `taskbar.h`; `Taskbar_SHCore_Init` is intentionally declared in `dll.h`, not `taskbar.h`, because loader initialization uses the central DLL init table; behavior changes must target `taskbar.c` or the concrete caller/loader owner; and SREV-004/SREV-228 remain concrete behavior owners for existing AppUserModelID and `IPropertyStore` fixes. |
| Topology | `shell32.dll load -> sh.c SH32_Init -> Taskbar_Init(module) -> taskbar.c installs shell32 taskbar hooks`; `shcore.dll load -> ldr.c DLL table -> Taskbar_SHCore_Init(module) declared by dll.h -> taskbar.c installs shcore AppUserModelID hooks`; `window creation / dialog creation -> gui.c / guidlg.c -> Taskbar_SetProcessAppUserModelId / Taskbar_SetWindowAppUserModelId -> taskbar.c AppUserModelID and property-store rewriting`; `property store request -> SHGetPropertyStoreForWindow -> Taskbar_SHGetPropertyStoreForWindow -> Taskbar IPropertyStore wrapper -> SREV-228 QueryInterface/property-store contract`. |
| Logic Risk | The high coverage score comes from the header naming taskbar boundary entry points. Treating `taskbar.h` as the runtime owner would hide the real owners: `taskbar.c` for behavior, `sh.c` and `ldr.c` for module init routing, and `gui.c` / `guidlg.c` for window lifecycle entry points. It would also blur the existing SREV split where SREV-004 and SREV-228 already own concrete fixes. |
| Official Shape | No new Windows/API runtime behavior is defined by this header. The official AppUserModelID, PEB/process-parameter, `IPropertyStore`, `SHGetPropertyStoreForWindow`, `IUnknown::QueryInterface`, and COM QueryInterface references remain in SREV-004 and SREV-228. This SREV is a local declaration/topology classification. |
| Fix | No source patch. This SREV records `taskbar.h` as a declaration/topology header and closes it as docs-only coverage. Future behavior patches should target `taskbar.c`, the concrete shell/loader/window caller, or the existing behavior-specific SREV owner. |
| Acceptance Gate | `docs/plan/check-srev-241.py` validates the draft-07 schema, header declaration shape, `taskbar.c` implementation topology, `sh.c` shell init caller, `ldr.c` SHCore loader edge, `gui.c` and `guidlg.c` window lifecycle callers, existing SREV-004/SREV-228 owner coverage, split ledger fragment, and absence of runtime owner code in this header; `docs/plan/check-srev-241.sh` is the targeted wrapper. Runtime/build gate: Windows DLL build continues to compile `taskbar.h` and wire taskbar lifecycle through `sh.c`, `ldr.c`, `gui.c`, `guidlg.c`, and `taskbar.c`; runtime behavior remains covered by existing and future concrete-owner SREV Windows gates. |
