# SREV-238: GUI Driver Header Topology Contract

## Stage

data -> schema -> boundary -> topology -> logic -> verify

## Evidence

After SREV-237, `Sandboxie/core/drv/gui.h` was the top unnamed reviewable core
file. Source readback shows it is the declaration header for the driver GUI
module. It includes `driver.h` and exposes `Gui_Init`, conditional
`Gui_Unload`, `Gui_InitProcess`, and `Gui_Check_OpenWinClass`.

The runtime owners are elsewhere:

- `Sandboxie/core/drv/gui.c` owns driver GUI API registration, per-process open
  window-class path initialization, `OpenWinClass` refresh, and the Vista+
  `API_GUI_CLIPBOARD` window-station / clipboard workaround.
- `Sandboxie/core/drv/gui_xp.c` owns legacy 32-bit XP win32k hook setup and
  unload behavior when `XP_SUPPORT` is enabled.
- `Sandboxie/core/drv/driver.c` owns driver initialization/unload ordering and
  calls `Gui_Init` / `Gui_Unload`.
- `Sandboxie/core/drv/process.c` owns process lifecycle sequencing and calls
  `Gui_Check_OpenWinClass` / `Gui_InitProcess`.
- SREV-096 already owns driver-side clipboard window-station reference
  lifetime, and SREV-134 owns the service-side clipboard probe data shape used
  by `Gui_InitClipboard`.

## Data

`Gui_Init`, `Gui_Unload`, `Gui_InitProcess`, `Gui_Check_OpenWinClass`,
`PROCESS`, `API_INIT_GUI`, `API_GUI_CLIPBOARD`, `OpenWinClass`,
`Process_GetPaths`, `Process_AddPath`, `Conf_Get`,
`PsGetProcessWin32WindowStation`, `ObReferenceObjectByHandle`,
`Gui_InitClipboard`, `Gui_FixClipboard`, `Gui_Api_Clipboard`, `gui.c`,
`gui_xp.c`, `driver.c`, and `process.c`.

## Schema

`GUI_DRIVER_HEADER_TOPOLOGY_CONTRACT` says:

- `gui.h` is the driver GUI module declaration header.
- The header may include `driver.h` and declare module lifecycle / process entry
  points that take or return local driver types.
- The header does not own API handler registration, XP win32k hook behavior,
  OpenWinClass path policy, process lifecycle sequencing, clipboard private
  layout discovery, window-station object references, or service-side clipboard
  probe ownership.
- Runtime behavior changes belong to `gui.c`, `gui_xp.c`, `driver.c`,
  `process.c`, or SbieSvc GUI/DriverAssist owners depending on the transition.
- Future changes to this header must prove driver initialization, process
  lifecycle, and GUI API topology before behavior claims.

## Topology

```text
DriverEntry / driver initialization
-> Driver_Init
-> Gui_Init
-> API_INIT_GUI / API_GUI_CLIPBOARD handler registration
-> optional XP win32k hook setup

process creation / image notification
-> Process_NotifyImage
-> Gui_Check_OpenWinClass
-> Gui_InitProcess
-> OpenWinClass path list becomes active for the process

SbieSvc GUI clipboard path
-> API_GUI_CLIPBOARD
-> gui.c references current process window station
-> private clipboard layout discovery or integrity rewrite
```

The header is the declaration node. It is not the owner of driver GUI policy,
XP hook ABI, user32/win32k behavior, clipboard memory lifetime, or process
lifecycle decisions.

## Logic Risk

The high coverage score comes from `gui.h` naming boundary-heavy entry points:
driver API registration, GUI/window-class process state, XP win32k hooks, and
window-station clipboard repair. Treating the header as the runtime owner would
hide the real boundary and encourage edits in a file that cannot enforce GUI
semantics. Behavior reviews must target the concrete owner that executes the
crossing.

## Official Shape

No new Windows/API runtime behavior is defined by this header. The official
window-station, clipboard, object-reference, and integrity references for the
underlying driver GUI clipboard behavior remain in SREV-096; the service-side
clipboard probe shape remains in SREV-134. This SREV is a local
declaration/topology classification.

## Fix

No source patch. This SREV records `gui.h` as a declaration/topology header and
closes it as docs-only coverage. Future behavior patches should target the
owner that executes the relevant driver API handler, XP hook, process lifecycle,
window-class path, or clipboard transition.

## Acceptance Gate

`docs/plan/check-srev-238.py` validates the draft-07 schema, header declaration
shape, `gui.c` implementation topology, `gui_xp.c` legacy hook topology,
`driver.c` initialization/unload callers, `process.c` lifecycle callers,
existing GUI/clipboard SREV owner coverage, split ledger fragment, and absence
of runtime owner code in this header.

Runtime/build gate: Windows driver build continues to compile `gui.h` and wire
GUI module lifecycle through `driver.c` / `process.c`; runtime behavior remains
covered by existing and future concrete-owner SREV Windows gates.
