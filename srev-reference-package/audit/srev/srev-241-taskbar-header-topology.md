# SREV-241: Taskbar Header Topology Contract

## Stage

data -> schema -> boundary -> topology -> logic -> verify

## Evidence

After SREV-240, `Sandboxie/core/dll/taskbar.h` was the top unnamed reviewable
core file. Source readback shows it is a small declaration header for shell
taskbar integration. It declares:

- `Taskbar_Init(HMODULE)`
- `Taskbar_SetProcessAppUserModelId(void)`
- `Taskbar_SetWindowAppUserModelId(HWND hwnd)`

The runtime owner is `Sandboxie/core/dll/taskbar.c`, not the header.
`taskbar.c` owns Shell/AppUserModelID hooks, `SHGetPropertyStoreForWindow`
wrapping, AppUserModelID prefixing, taskbar property rewriting, and the local
property-store COM wrapper. `Sandboxie/core/dll/sh.c` calls `Taskbar_Init` from
the Shell initialization path. `Sandboxie/core/dll/gui.c` and
`Sandboxie/core/dll/guidlg.c` call the process/window AppUserModelID helpers
from window-creation and dialog paths.

The loader edge for `Taskbar_SHCore_Init` is not declared by `taskbar.h`;
`Sandboxie/core/dll/dll.h` exposes that init function to `ldr.c` for the
`shcore.dll` path. That split matters because `taskbar.h` is not the complete
taskbar module ABI surface.

Existing SREVs already own concrete behavior:

- SREV-004 owns the AppUserModelID process-parameter workaround in `taskbar.c`.
- SREV-228 owns the `IPropertyStore` / `QueryInterface` wrapper contract in
  `propsys.h` and `taskbar.c`.

## Data

`taskbar.h`, `taskbar.c`, `Taskbar_Init`, `Taskbar_SetProcessAppUserModelId`,
`Taskbar_SetWindowAppUserModelId`, `Taskbar_SHCore_Init`, `sh.c`, `gui.c`,
`guidlg.c`, `ldr.c`, `dll.h`, `SetCurrentProcessExplicitAppUserModelID`,
`GetCurrentProcessExplicitAppUserModelID`, `SHGetPropertyStoreForWindow`,
`IPropertyStore`, `PKEY_AppUserModel_ID`, `PKEY_AppUserModel_RelaunchCommand`,
`PKEY_AppUserModel_RelaunchDisplayNameResource`, SREV-004, and SREV-228.

## Schema

`TASKBAR_HEADER_TOPOLOGY_CONTRACT` says:

- `taskbar.h` is the declaration header for shell taskbar entry points used by
  shell and GUI hook modules.
- `taskbar.c` owns the implementation, hook installation, AppUserModelID state,
  property-store wrapper, COM behavior, and Shell property rewriting.
- `sh.c`, `gui.c`, and `guidlg.c` are legal local callers for the functions
  declared by `taskbar.h`.
- `Taskbar_SHCore_Init` is intentionally declared in `dll.h`, not `taskbar.h`,
  because loader initialization uses the central DLL init table.
- Behavior changes must target `taskbar.c` or the concrete caller/loader owner,
  not the declaration header.
- SREV-004 and SREV-228 remain the concrete behavior owners for existing
  AppUserModelID and `IPropertyStore` fixes.

## Topology

```text
shell32.dll load
-> sh.c SH32_Init
-> Taskbar_Init(module)
-> taskbar.c installs shell32 taskbar hooks

shcore.dll load
-> ldr.c DLL table
-> Taskbar_SHCore_Init(module) declared by dll.h
-> taskbar.c installs shcore AppUserModelID hooks

window creation / dialog creation
-> gui.c / guidlg.c
-> Taskbar_SetProcessAppUserModelId / Taskbar_SetWindowAppUserModelId
-> taskbar.c AppUserModelID and property-store rewriting

property store request
-> SHGetPropertyStoreForWindow
-> Taskbar_SHGetPropertyStoreForWindow
-> Taskbar IPropertyStore wrapper
-> SREV-228 QueryInterface/property-store contract
```

The header is the declaration node for selected shell/GUI callers. It does not
own the Shell API contract, COM identity, property-store forwarding, process
parameter workaround, loader table, or GUI window-creation policy.

## Logic Risk

The high coverage score comes from the header naming taskbar boundary entry
points. Treating `taskbar.h` as the runtime owner would hide the real owners:
`taskbar.c` for behavior, `sh.c` and `ldr.c` for module init routing, and
`gui.c` / `guidlg.c` for window lifecycle entry points. It would also blur the
existing SREV split where SREV-004 and SREV-228 already own concrete fixes.

## Official Shape

No new Windows/API runtime behavior is defined by this header. The official
AppUserModelID, PEB/process-parameter, `IPropertyStore`,
`SHGetPropertyStoreForWindow`, `IUnknown::QueryInterface`, and COM
QueryInterface references remain in SREV-004 and SREV-228. This SREV is a local
declaration/topology classification.

## Fix

No source patch. This SREV records `taskbar.h` as a declaration/topology header
and closes it as docs-only coverage. Future behavior patches should target
`taskbar.c`, the concrete shell/loader/window caller, or the existing
behavior-specific SREV owner.

## Acceptance Gate

`docs/plan/check-srev-241.py` validates the draft-07 schema, header declaration
shape, `taskbar.c` implementation topology, `sh.c` shell init caller, `ldr.c`
SHCore loader edge, `gui.c` and `guidlg.c` window lifecycle callers, existing
SREV-004/SREV-228 owner coverage, split ledger fragment, and absence of runtime
owner code in this header.

Runtime/build gate: Windows DLL build continues to compile `taskbar.h` and wire
taskbar lifecycle through `sh.c`, `ldr.c`, `gui.c`, `guidlg.c`, and
`taskbar.c`; runtime behavior remains covered by existing and future
concrete-owner SREV Windows gates.
