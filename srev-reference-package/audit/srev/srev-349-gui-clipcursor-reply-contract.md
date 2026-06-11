# SREV-349: GUI ClipCursor Reply Contract

| Field | Content |
|---|---|
| Stage | schema -> boundary -> topology -> action -> verify |
| Input artifact | `Sandboxie/core/dll/guimisc.c`, `Sandboxie/core/svc/GuiServer.cpp`, `Sandboxie/core/svc/GuiWire.h`, `Gui_CallProxy`, and Microsoft `ClipCursor` / DPI awareness documentation |
| Output artifact | Source patch, draft-07 schema, checker, and ledger fragment |
| Owner | `GUI_CLIP_CURSOR` request/reply ABI between the sandbox DLL and SbieSvc GUI proxy |
| Acceptance gate | Targeted checker validates official references, reply first-field status shape, service-side `ClipCursor` return/error propagation, DLL-side `BOOL` / `SetLastError` restoration, stale TODO removal, and ledger fragment |

## Data

`Gui_ClipCursor` hooks Win32 `ClipCursor`. Without the proxy service, it calls
the native API directly. With the proxy service, it sends `GUI_CLIP_CURSOR` to
SbieSvc because the sandboxed process may not have the window-station access
required to modify the shared cursor clip rectangle.

Before this SREV, `ClipCursorSlave` called `ClipCursor(rect)` and ignored its
return value. A nearby comment said the call seemed to randomly fail and left a
TODO to add a reply and return the real value. The DLL asked `Gui_CallProxy` for
only `sizeof(ULONG)` and treated any reply as success, so the caller could see
`TRUE` even when the service-side `ClipCursor` failed.

`Gui_CallProxy` also has a wire-shape constraint: if the reply starts with a
nonzero `ULONG`, it treats that value as a status and fails the proxy call.
Therefore a `ClipCursor` reply cannot put the Win32 `BOOL` return value in the
first field.

## Official Shape

Microsoft documents `ClipCursor` as returning nonzero on success and zero on
failure. Extended error information is retrieved with `GetLastError`. Passing
`NULL` releases the cursor so it can move anywhere on the screen. Microsoft also
documents the cursor as a shared resource and requires the caller to have
`WINSTA_WRITEATTRIBUTES` access to the window station.

The local DPI bridge uses `GetThreadDpiAwarenessContext` in the DLL and
`SetThreadDpiAwarenessContext` in SbieSvc. Microsoft documents
`SetThreadDpiAwarenessContext` as returning the old context so it can be
restored after the temporary override.

Official references:

- `https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-clipcursor`
- `https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setthreaddpiawarenesscontext`
- `https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-getthreaddpiawarenesscontext`

## Boundary

`GUI_CLIP_CURSOR` is a Win32 API broker edge. The service becomes the execution
owner for the host-side `ClipCursor` call, but the sandboxed caller still owns
the Win32-observable return shape.

The reply ABI must separate transport status from Win32 result:

```text
status = proxy transport / request handling status
error  = Win32 GetLastError value for ClipCursor failure
retval = ClipCursor BOOL return value
```

## Topology

```text
sandboxed caller
  -> Gui_ClipCursor(lpRect)
  -> GUI_CLIP_CURSOR_REQ { have_rect, RECT, dpi_awareness_ctx }
  -> ClipCursorSlave
  -> optional SetThreadDpiAwarenessContext(request context)
  -> ClipCursor(rect or NULL)
  -> GUI_CLIP_CURSOR_RPL { status=0, error, retval }
  -> restore old DPI awareness context
  -> Gui_ClipCursor sets LastError and returns retval
```

## Logic Risk

Returning success for a failed brokered `ClipCursor` violates the Win32 API
shape. Applications and games that use cursor confinement may believe they own
the clip rectangle when SbieSvc failed to set it. Conversely, treating a
nonzero `BOOL` as the first reply field would trigger `Gui_CallProxy`'s
nonzero-status path and make successful calls fail. The ABI needs an explicit
status/error/retval reply.

## Fix

`GuiWire.h` now defines `GUI_CLIP_CURSOR_RPL` with `status`, `error`, and
`retval`. `ClipCursorSlave` records the service-side `ClipCursor` return value
and failure error, sets `args->rpl_len`, and restores the previous DPI awareness
context. `Gui_ClipCursor` now requests the full reply, returns `retval`, and
restores `GetLastError` from the reply.

The `Gui_BlockInterferenceControl` local deny path, direct native path when the
GUI proxy is disabled, active-clip tracking, and exit-time `Gui_ResetClipCursor`
behavior are unchanged.

## Acceptance Gate

`docs/plan/check-srev-349.py` validates the draft-07 schema, official
references, `GUI_CLIP_CURSOR_RPL` ABI shape, `Gui_CallProxy` first-field status
constraint, service-side `ClipCursor` `retval/error` capture, DLL-side
`SetLastError` and `BOOL` return, stale TODO removal, combined ledger entry,
and split ledger fragment.

Runtime gate: Windows SbieSvc/DLL build plus `ClipCursor(&rect)` success and
failure smoke proving brokered callers receive the same `BOOL` / `GetLastError`
shape as native `ClipCursor`, including `ClipCursor(NULL)` release and DPI
awareness restore behavior.
