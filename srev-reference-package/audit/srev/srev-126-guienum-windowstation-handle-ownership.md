# SREV-126 GUI Enum Window Station Handle Ownership

## Data

Owner file:

```text
Sandboxie/core/dll/guienum.c
```

Reviewed nodes:

```text
Gui_CreateWindowStationW
Gui_CreateWindowStationA
Gui_Dummy_WinSta
GetProcessWindowStation
CreateWindowStationW
CreateWindowStationA
CloseWindowStation
DuplicateHandle
SECURITY_ATTRIBUTES.bInheritHandle
DUPLICATE_SAME_ACCESS
UseSbieWndStation
DLL_IMAGE_GOOGLE_CHROME
DLL_IMAGE_MOZILLA_FIREFOX
```

## Schema

`GUIENUM_WINDOWSTATION_HANDLE_OWNERSHIP` defines these local contracts:

- `Gui_Dummy_WinSta` is a process window-station handle captured from the
  process window-station topology.
- A handle returned by `GetProcessWindowStation` is process-owned and must not
  be closed by ordinary callers.
- A handle returned from `CreateWindowStationW` or `CreateWindowStationA` is
  caller-owned and is expected to be releasable with `CloseWindowStation`.
- The `CreateWindowStationW/A` fallback must not return `Gui_Dummy_WinSta`
  directly.
- When the fallback uses `Gui_Dummy_WinSta`, it returns a duplicate handle
  produced by `DuplicateHandle` in the current process with
  `DUPLICATE_SAME_ACCESS`.
- The duplicate inheritability follows
  `SECURITY_ATTRIBUTES.bInheritHandle` when `lpsa` is supplied.
- Native `CreateWindowStationW/A`, fallback policy predicates, logging, and
  failure return shape are unchanged.

## Topology

```text
process window station
  -> GetProcessWindowStation()
  -> Gui_Dummy_WinSta
  -> DuplicateHandle(current process, Gui_Dummy_WinSta, current process)
  -> caller-owned CreateWindowStationW/A fallback result
  -> caller may CloseWindowStation(duplicate)
```

The native path remains:

```text
Gui_CreateWindowStationW/A
  -> __sys_CreateWindowStationW/A(...)
  -> return native handle on success
```

The fallback policy remains:

```text
Gui_Dummy_WinSta exists
  && (UseSbieWndStation || Chrome || Firefox)
  -> duplicate dummy window-station handle
```

## Logic Risk

The old fallback returned `Gui_Dummy_WinSta` directly as if it were a
`CreateWindowStation` result. That crosses two incompatible ownership contracts:
Microsoft documents that `GetProcessWindowStation` returns a process-associated
handle that must not be closed, while `CreateWindowStation` returns a handle
that the caller must later free with `CloseWindowStation`. A caller that follows
the public `CreateWindowStation` contract could therefore attempt to close the
process current window-station handle, corrupting the local GUI topology or
failing in a way that does not match a real created/opened window-station
handle.

The correct local repair is to create a caller-owned duplicate at the existing
fallback boundary. It does not change whether Sandboxie uses the fallback, which
images receive it, or how the native `CreateWindowStation` call is attempted.

## Official Shape

- https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-getprocesswindowstation
- https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-createwindowstationw
- https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-closewindowstation
- https://learn.microsoft.com/en-us/windows/win32/api/handleapi/nf-handleapi-duplicatehandle

## Fix

`Gui_CreateWindowStationW` and `Gui_CreateWindowStationA` now duplicate
`Gui_Dummy_WinSta` into the current process before returning it from the
fallback path. The duplicate uses `DUPLICATE_SAME_ACCESS`, and its inherit flag
is derived from `lpsa->bInheritHandle` when a `SECURITY_ATTRIBUTES` pointer was
provided.

If duplication fails, the functions continue to the existing log-and-zero
failure path. No native `CreateWindowStationW/A` call, fallback predicate,
browser exception, log message, or non-fallback return behavior changed.

## Acceptance Gate

Source gate:

```bash
python3 docs/plan/check-srev-126.py
bash docs/plan/check-srev-126.sh
```

Runtime/build gate still required:

- Windows build for `guienum.c`.
- `CreateWindowStationW/A` fallback smoke with `Gui_Dummy_WinSta` proving the
  returned handle is a duplicate and can be closed without closing
  `Gui_Dummy_WinSta`.
- Inheritability matrix with null `lpsa`, `bInheritHandle=FALSE`, and
  `bInheritHandle=TRUE`.
- Native `CreateWindowStationW/A` success smoke proving unchanged direct return.
- Duplicate failure injection proving the existing log-and-zero failure path.
