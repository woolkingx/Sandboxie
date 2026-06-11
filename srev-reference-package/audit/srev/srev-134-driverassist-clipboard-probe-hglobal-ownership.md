# SREV-134: DriverAssist Clipboard Probe HGLOBAL Ownership

## Stage Gate

| Field | Value |
|---|---|
| Stage | action |
| Input artifact | `Sandboxie/core/svc/DriverAssistStart.cpp`, `Sandboxie/core/drv/gui.c`, Microsoft global-memory and clipboard references |
| Output artifact | `docs/plan/srev-134-driverassist-clipboard-probe-hglobal-ownership.schema.json`, `docs/plan/check-srev-134.py`, `docs/plan/check-srev-134.sh`, ledger row |
| Owner | `DriverAssist::InitClipboard` and driver-side `Gui_InitClipboard` probe input |
| Acceptance gate | source checker plus full SREV/KPATH/core coverage matrix; Windows clipboard runtime remains required |

## Evidence

`Sandboxie/core/svc/DriverAssistStart.cpp` was the highest-ranked unnamed reviewable core file after SREV-133. `DriverAssist::InitClipboard` creates dummy clipboard entries on Vista and later so driver-side `Gui_InitClipboard` can infer the internal clipboard item layout. `Sandboxie/core/drv/gui.c` says the service has placed four unique items on the clipboard, then scans the kernel clipboard item array for the format sequence `0x111111`, `0x222222`, `0x333333`, and `0x444444`.

Before this SREV, the service created only two movable memory objects, reused each object for two clipboard formats, and dereferenced `GlobalLock` return values without checking for `NULL`. That conflicted with the local probe contract of four unique items and with the global-memory API failure shape.

Microsoft documents `GlobalAlloc` as returning `NULL` on failure. Microsoft documents `GlobalLock` as returning a pointer to the first byte of the memory block and `NULL` on failure. Microsoft documents `SetClipboardData` as transferring a memory object to the clipboard on success and says the object must be movable for memory formats. Microsoft documents `EmptyClipboard` as emptying the clipboard before new data is placed and failing if an application calls it when the clipboard is not open.

Official references:

- https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-globalalloc
- https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-globallock
- https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setclipboarddata
- https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-emptyclipboard

## Data

`DriverAssist::InitClipboard`, `Formats[4]`, four `HGLOBAL` probe objects, `GlobalAlloc`, `GlobalLock`, `GlobalUnlock`, `SetClipboardData`, `OpenClipboard`, `EmptyClipboard`, `CloseClipboard`, `GlobalFree`, `API_GUI_CLIPBOARD`, driver-side `Gui_InitClipboard`, and probe formats `0x111111`, `0x222222`, `0x333333`, `0x444444`.

## Schema

`DRIVERASSIST_CLIPBOARD_PROBE_HGLOBAL_OWNERSHIP` says:

- `InitClipboard` creates four unique movable memory objects for the four driver-probe clipboard formats.
- `GlobalAlloc` failure prevents clipboard probing and still releases every allocated local object.
- `GlobalLock` failure prevents clipboard probing and still releases every allocated local object.
- `InitClipboard` dereferences a `GlobalLock` pointer only after the pointer is non-null.
- `SetClipboardData` receives one unique `HGLOBAL` per private probe format.
- `InitClipboard` invokes `API_GUI_CLIPBOARD` only after the dummy clipboard items have been placed.
- `InitClipboard` empties the clipboard after the driver probe and before locally freeing the dummy private-format objects.
- `Gui_InitClipboard` still observes the same four format markers in the same order.
- Vista+ clipboard structure probing and retry topology are unchanged.

## Topology

The legal probe topology is:

```text
Vista+ service startup
  -> allocate four movable dummy HGLOBAL objects
  -> lock/check/init/unlock every object
  -> retry OpenClipboard
  -> EmptyClipboard
  -> SetClipboardData for 0x111111 / 0x222222 / 0x333333 / 0x444444
  -> API_GUI_CLIPBOARD asks driver to infer item layout
  -> EmptyClipboard
  -> CloseClipboard
  -> release local dummy objects
```

The driver-side observation topology remains:

```text
Gui_InitClipboard
  -> reference window-station clipboard
  -> require at least four items
  -> scan format ids 0x111111 -> 0x222222 -> 0x333333 -> 0x444444
  -> derive item length and integrity index
```

## Logic Risk

The service and driver sides disagreed on the data shape: the driver comment and scanner expect four unique dummy items, but the service reused two memory objects across four formats. Reusing clipboard memory objects makes ownership ambiguous around `SetClipboardData` / `EmptyClipboard`, and dereferencing an unchecked `GlobalLock` result can crash the service under low-memory or handle-state failure. The correct local repair is to make the probe data shape match the driver observation shape with four independent dummy objects and checked lock pointers.

This does not change clipboard format ids, the driver scanner, retry count, Vista+ gating, or the private kernel clipboard structure inference policy.

## Fix

`DriverAssist::InitClipboard` now allocates four `GMEM_MOVEABLE` `HGLOBAL` objects, initializes each only after `GlobalLock` returns a non-null pointer, and calls `SetClipboardData` once per format using the matching unique object. If allocation or lock initialization fails, the clipboard probe is skipped and every allocated dummy object is released.

## Acceptance Gate

`docs/plan/check-srev-134.py` validates the draft-07 schema, official references, four unique dummy `HGLOBAL` slots, checked `GlobalAlloc` and `GlobalLock` topology, one `SetClipboardData` call per probe format through the `Formats` array, unchanged `API_GUI_CLIPBOARD` / `EmptyClipboard` / `CloseClipboard` order, driver-side four-format scanner evidence, and ledger entry. `docs/plan/check-srev-134.sh` is the matrix wrapper.

Runtime/build gate: Windows service build for `DriverAssistStart.cpp`, Vista+ clipboard init smoke proving `API_GUI_CLIPBOARD` detects item length and integrity index, allocation failure injection proving no `GlobalLock` NULL dereference and no dummy object leak, clipboard-open retry smoke proving unopened clipboard leaves every local object freed, and ordinary clipboard operations proving integrity correction still works.
