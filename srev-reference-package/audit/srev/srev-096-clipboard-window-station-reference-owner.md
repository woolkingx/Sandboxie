# SREV-096: Clipboard Window-Station Reference Owner

## Data

`Sandboxie/core/drv/gui.c` owns the driver-side `API_GUI_CLIPBOARD` operation
that adjusts clipboard item integrity levels for Vista-and-later UIPI
clipboard access. The local data path is:

```text
sandboxed process closes clipboard
core/dll/guimisc.c asks SbieSvc to close/fix clipboard
core/svc/GuiServer.cpp opens the clipboard and forces delayed rendering
SbieDrv API_GUI_CLIPBOARD reads the current process window station object
private clipboard item list at Dyndata_Config.Clipboard_offset
clipboard item integrity ULONGs are raised to the service IL value
```

## Official Shape

Microsoft documents a window station as a securable object associated with a
process. A window station contains a clipboard, an atom table, and desktop
objects. Microsoft also documents `GetProcessWindowStation` as returning the
calling process's current window-station handle, and says that handle must not
be closed by the caller.

Microsoft documents `ObReferenceObjectByHandle` as returning a pointer to the
object body and incrementing the object's pointer reference count on success.
That reference prevents deletion while the pointer is referenced. Microsoft
documents the object lifecycle rule as a paired contract: each successful object
reference routine call must be matched with `ObDereferenceObject` after the
driver is done using the pointer.

Microsoft documents clipboard delayed rendering as `SetClipboardData(format,
NULL)`, with real data rendered only when requested. `GetClipboardData` requires
an opened clipboard and can cause format conversion or delayed rendering. This
matches the SbieSvc-side loop that opens the clipboard, enumerates formats, and
calls `GetClipboardData` before the driver-side integrity fix.

Microsoft documents Mandatory Integrity Control as assigning integrity levels to
security principals and securable objects. That is the public security model
behind the local private-layout workaround; the private win32k clipboard item
layout remains undocumented and must stay version/runtime gated.

```text
https://learn.microsoft.com/en-us/windows/win32/winstation/about-window-stations-and-desktops
https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-getprocesswindowstation
https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-obreferenceobjectbyhandle
https://learn.microsoft.com/en-us/windows-hardware/drivers/kernel/life-cycle-of-an-object
https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setclipboarddata
https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-getclipboarddata
https://learn.microsoft.com/en-us/windows/win32/dataxchg/clipboard-operations
https://learn.microsoft.com/en-us/windows/win32/secauthz/mandatory-integrity-control
```

## Schema

Local schema:

```text
docs/plan/srev-096-clipboard-window-station-reference-owner.schema.json
```

The clipboard window-station reference contract is:

```text
API_GUI_CLIPBOARD may inspect private clipboard state only from SbieSvc
the current process window-station handle is only a handle source
ObReferenceObjectByHandle must hold the window-station object while clipboard memory is read or modified
the returned clipboard pointer is valid only inside the held window-station reference scope
Gui_InitClipboard must release the reference on every exit after acquisition
Gui_FixClipboard must release the reference after mutating clipboard items
private clipboard layout discovery remains Dyndata/version gated
SbieSvc remains the clipboard open/lock and delayed-rendering owner
```

## Topology

```text
Gui_CloseClipboard
  -> Gui_CallProxyEx(GUI_CLOSE_CLIPBOARD)
  -> GuiServer::CloseClipboardSlave
  -> OpenClipboard(NULL)
  -> SbieApi_Call(API_GUI_CLIPBOARD, 0x4000)
  -> EnumClipboardFormats / GetClipboardData delayed-render forcing
  -> SbieDrv Gui_Api_Clipboard
  -> MyIsCallerMyServiceProcess gate
  -> PsGetProcessWin32WindowStation(PsGetCurrentProcess())
  -> ObReferenceObjectByHandle(window-station handle)
  -> read or mutate private clipboard items while reference is held
  -> ObDereferenceObject(window-station object)
  -> CloseClipboard()
```

## Logic Risk

Before this SREV, `Gui_GetClipboard` called `ObReferenceObjectByHandle`,
immediately called `ObDereferenceObject`, and then returned a pointer computed
inside the dereferenced window-station object. That expressed the wrong API
shape: the reference was released before the private clipboard memory was read
or modified by `Gui_InitClipboard` or `Gui_FixClipboard`.

The clipboard layout itself is private and still risky, but this SREV does not
try to redesign it from local guesswork. The official owner rule is narrower:
hold the object reference for the whole period in which the driver uses the
object-body pointer.

## Fix

`Gui_GetClipboard` was replaced by an explicit reference-scoped pair:
`Gui_ReferenceClipboard` and `Gui_DereferenceClipboard`. The helper returns a
`GUI_CLIPBOARD_REF` containing both the private clipboard pointer and the held
window-station object reference.

`Gui_InitClipboard` now releases the reference through a single `finish:` path
after any exit following acquisition. `Gui_FixClipboard` releases the reference
after the item loop. The private layout scan, integrity values, `SbieSvc` caller
gate, delayed-rendering loop, and `Dyndata_Config.Clipboard_offset` policy are
unchanged.

## Acceptance Gate

`docs/plan/check-srev-096.py` validates the draft-07 schema, official
references, SbieSvc-only gate, service-side delayed-rendering path, private
layout discovery constants, removal of the stale immediate-deref-return shape,
the new reference-scoped helper pair, reference release on all post-acquisition
`Gui_InitClipboard` exits, and reference release after `Gui_FixClipboard`
mutation. `docs/plan/check-srev-096.sh` is the matrix wrapper.

Runtime gate: Windows Vista+ clipboard matrix with UAC/UIPI on and off, delayed
rendering formats, ordinary immediate formats, viewer/listener notification
race observation, service process `0x4000` integrity fix, and regression checks
for copy from sandbox to host without system hang.
