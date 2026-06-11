# SREV-090: GUI Title RealGetWindowClass Buffer Shape

## Data

`Sandboxie/core/dll/guititle.c` owns the DLL-side window-title decoration gate
and title string helpers. `gui.c`, `guimsg.c`, `guienum.c`, and `guicon.c`
consume those helpers when they rewrite or expose window text. The
comment-admitted shape is:

```text
window handle
GWL_STYLE / WS_CAPTION titlebar classification
window rectangle and client origin
RealGetWindowClassW output buffer
Office hidden splash/dialog class skip list
Edit control exclusion
GetWindowText / helper-consumer title rewrite path
```

## Official Shape

Microsoft documents `RealGetWindowClassW` as retrieving a window-type string
into an output buffer. Its third parameter, `cchClassNameMax`, is the length in
characters of the class-name buffer. The return value is the number of
characters copied, or zero on failure.

Microsoft documents `GetWindowLongW(GWL_STYLE)` as retrieving the window style.
The window-style table defines `WS_CAPTION` as a style for a window with a title
bar.

Microsoft documents `GetWindowRect` as returning the window bounding rectangle
in screen coordinates, and `ClientToScreen` as converting a client-area point to
screen coordinates. This is the public shape used by the local custom-titlebar
heuristic.

Microsoft documents `GetWindowTextW` as copying a window title/control text into
a character-counted output buffer, with truncation and null termination when the
text is too long. Microsoft documents `SetWindowTextW` as changing a window
title/control text and sending `WM_SETTEXT` when the target window belongs to
the current process. `WM_SETTEXT` carries a pointer to a null-terminated window
text string.

```text
https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-realgetwindowclassw
https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-getwindowlongw
https://learn.microsoft.com/en-us/windows/win32/winmsg/window-styles
https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-getwindowrect
https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-clienttoscreen
https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-getwindowtextw
https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setwindowtextw
https://learn.microsoft.com/en-us/windows/win32/winmsg/wm-settext
```

## Schema

Local schema:

```text
docs/plan/srev-090-guititle-realgetwindowclass-buffer-shape.schema.json
```

The class-buffer contract is:

```text
RealGetWindowClassW cchClassNameMax is a WCHAR character count, not a byte count
the class-name buffer capacity is passed as ARRAYSIZE(clsnm)
the class-name string is locally NUL-terminated before wcsstr / _wcsicmp consumers
hidden Office caption-class skip checks run only after legal class-buffer shape
Edit controls remain excluded from title suffix creation
title helper consumers keep gating title mutation through Gui_ShouldCreateTitle before GetWindowText / SendMessage / WM_SETTEXT paths
```

## Topology

```text
HWND
  -> Gui_ShouldCreateTitle
  -> public window style / rectangle / class query gates
  -> Office hidden-caption skip list
  -> Edit control exclusion
  -> Gui_CreateTitleW/A or Gui_FixTitleW/A
  -> helper consumers in gui.c / guimsg.c / guienum.c / guicon.c
```

The title path crosses a documented user32 boundary before local compatibility
classification. The local class-name buffer is owned by `guititle.c`; user32
only receives the buffer and its character capacity. The actual title mutation
call sites are separate GUI owners that consume `Gui_ShouldCreateTitle` and the
title helpers.

## Logic Risk

Before this patch, the Office splash/class-name compatibility block passed
`sizeof(clsnm) - 1` to `RealGetWindowClassW` for `WCHAR clsnm[256]`. That value
is a byte count minus one, not a character count. On WCHAR builds it advertises a
511-character output buffer for a 256-WCHAR local array.

This is exactly the shape bug the official API definition prevents: class data
from user32 can be copied using a capacity larger than the stack buffer. The
subsequent `wcsstr` and `_wcsicmp` consumers require a bounded, null-terminated
class string.

## Fix

`Gui_ShouldCreateTitle` now passes `ARRAYSIZE(clsnm)` as the
`RealGetWindowClassW` buffer length, clamps defensive oversized return values,
and writes a local NUL terminator before the Office class skip list and `Edit`
class comparison.

The stale anonymous `$Workaround$` comment was removed. The documented behavior
is now the data shape: the buffer capacity is characters, and the local string is
terminated before local classification.

## Acceptance Gate

`docs/plan/check-srev-090.py` validates the draft-07 schema, official Win32
references, `ARRAYSIZE(clsnm)` use, defensive NUL termination, stale byte-count
call removal, stale anonymous workaround comment removal, Office class skip list
preservation, `Edit` exclusion preservation, helper-consumer title-rewrite gate
preservation, and ledger entry.

Windows gate: Office splash / hidden caption windows still skip title mutation;
normal top-level captioned windows still receive the Sandboxie title marker;
custom-titlebar windows still skip mutation; `Edit` controls remain excluded;
long or unusual class names do not corrupt the stack. Source-level gates do not
prove this runtime path.
