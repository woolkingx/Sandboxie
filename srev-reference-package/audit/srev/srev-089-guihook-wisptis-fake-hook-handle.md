# SREV-089: GUI Hook WISPTIS Fake Hook Handle

## Data

`Sandboxie/core/dll/guihook.c` owns the DLL-side `SetWindowsHookExA/W` and
`UnhookWindowsHookEx` hook boundary. The comment-admitted shape is:

```text
WISPTIS process image type
WH_MOUSE_LL low-level mouse hook
suppressed SetWindowsHookExW request
fake HHOOK return value
UnhookWindowsHookEx input handle
Sandboxie pseudo-global GUI_HOOK pointer handles
real user32 HHOOK handles
```

## Official Shape

Microsoft documents `SetWindowsHookExW` as installing an application-defined
hook procedure into a hook chain and returning a hook handle on success or NULL
on failure.

Microsoft documents `WH_MOUSE_LL` as a low-level mouse hook. The
`LowLevelMouseProc` page states that the hook is not injected into another
process; the context switches back to the installing process and the callback is
called in its original context. It also states that the installing thread must
have a message loop.

Microsoft documents `UnhookWindowsHookEx` as removing a hook procedure installed
by `SetWindowsHookEx`; its `hhk` parameter is a hook handle obtained by a
previous `SetWindowsHookEx` call.

Microsoft documents hook chaining through `CallNextHookEx`; for low-level mouse
hooks, failing to pass unprocessed notifications to the next hook can make other
applications behave incorrectly.

```text
https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setwindowshookexw
https://learn.microsoft.com/en-us/windows/win32/winmsg/lowlevelmouseproc
https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-unhookwindowshookex
https://learn.microsoft.com/en-us/windows/win32/winmsg/about-hooks
```

## Schema

Local schema:

```text
docs/plan/srev-089-guihook-wisptis-fake-hook-handle.schema.json
```

The fake-handle contract is:

```text
the WISPTIS WH_MOUSE_LL compatibility block returns a non-NULL process-local fake HHOOK
the fake HHOOK has an owner-local cookie address rather than a magic integer
UnhookWindowsHookEx consumes that fake HHOOK locally before pointer-shape probing
real HHOOK values still forward to user32 UnhookWindowsHookEx
Sandboxie pseudo-global GUI_HOOK pointer handles keep their existing owner path
this SREV does not broaden WISPTIS hook suppression policy
```

## Topology

```text
WISPTIS SetWindowsHookExW(WH_MOUSE_LL)
  -> Gui_SetWindowsHookExW compatibility block
  -> process-local fake HHOOK cookie
  -> later UnhookWindowsHookEx(fake)
  -> Gui_UnhookWindowsHookEx local fake-cookie success
```

Other hook paths remain:

```text
non-injecting / thread-specific / hMod NULL hook
  -> user32 SetWindowsHookEx
  -> user32 HHOOK
  -> user32 UnhookWindowsHookEx

sandbox pseudo-global injected hook
  -> GUI_HOOK allocation
  -> GUI_HOOK* fake handle
  -> Sandboxie unhook owner path
```

## Logic Risk

Before this patch, the WISPTIS block returned the fixed integer
`0x12345678` as a fake `HHOOK`. `Gui_UnhookWindowsHookEx` distinguishes real
and Sandboxie fake handles through pointer alignment and then probes aligned
values as possible `GUI_HOOK*` pointers. The fixed integer is aligned on both
32-bit and 64-bit builds, so a later unhook can enter the pointer-probe path
with a value that is neither a real user32 hook handle nor a Sandboxie-owned
`GUI_HOOK` allocation.

The official API shape allows an application to pass a hook handle obtained from
`SetWindowsHookEx` back to `UnhookWindowsHookEx`. If Sandboxie synthesizes a
successful hook handle for compatibility, that handle needs an owner-local
identity and a matching unhook path.

## Fix

The WISPTIS low-level mouse hook block now returns the address of a process-local
static cookie as its fake `HHOOK`. `Gui_UnhookWindowsHookEx` consumes that cookie
locally before the existing pointer-alignment and `GUI_HOOK` probing path.

## Acceptance Gate

`docs/plan/check-srev-089.py` validates the draft-07 schema, official hook
references, WISPTIS `WH_MOUSE_LL` block evidence, static fake-cookie declaration,
cookie return from `SetWindowsHookExW`, local fake-cookie unhook success before
pointer probing, stale magic handle removal, and ledger entry.

Windows gate: WISPTIS inside the sandbox receives a successful blocked
`SetWindowsHookExW(WH_MOUSE_LL)` result, can later unhook that result without
probing arbitrary memory or calling user32 with a fake handle, and ordinary
thread-specific / low-level / pseudo-global hook behavior remains unchanged.
Source-level gates do not prove this runtime path.
