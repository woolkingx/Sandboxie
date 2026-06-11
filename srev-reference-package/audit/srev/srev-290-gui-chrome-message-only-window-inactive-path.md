# SREV-290: GUI Chrome Message-Only Window Inactive Path

## Stage Gate

| Field | Value |
|---|---|
| Stage | schema -> boundary -> topology -> verify |
| Input artifact | `Sandboxie/core/dll/gui.c`, SREV-084, Microsoft CreateWindowEx/window-feature/DDE references |
| Output artifact | Source comment owner, draft-07 schema, targeted checker, ledger fragment |
| Owner | `Gui_CreateWindowExW` inactive Chrome message-only window branch |
| Acceptance gate | Targeted checker validates official references, inactive branch shape, CreateWindowEx/HWND_MESSAGE/DDE topology, SREV-084 adjacency, stale wording removal, and ledger fragment |

## Data

`Gui_CreateWindowExW` contains an inactive legacy Chrome branch:

```c
/*if (Dll_ChromeSandbox) {
    dwStyle |= WS_CHILD;
    hWndParent = HWND_MESSAGE;
}*/
```

The old comment described an observed Chrome child-window / DDE broadcast
problem and then stated that the branch is no longer used because it breaks
Chrome hardware acceleration. The behavior is already inactive; this SREV
records the legal topology so it is not revived from stale symptom wording.

## Official Shape

Microsoft documents `CreateWindowExW` as creating an overlapped, pop-up, or
child window. Its `hWndParent` parameter supplies the parent or owner window.

Microsoft documents message-only windows as windows created by passing
`HWND_MESSAGE` as the `hWndParent` parameter to `CreateWindowEx`. Message-only
windows are not visible, have no z-order, cannot be enumerated, and do not
receive broadcast messages.

Microsoft documents DDE as a window-message protocol. DDE clients commonly
initiate conversations by sending `WM_DDE_INITIATE`; the client broadcasts this
message to all top-level windows through `SendMessage(HWND_BROADCAST, ...)`
unless it already has a target server window.

Official references:

- `https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-createwindowexw`
- `https://learn.microsoft.com/en-us/windows/win32/winmsg/window-features`
- `https://learn.microsoft.com/en-us/windows/win32/dataxchg/about-dynamic-data-exchange`
- `https://learn.microsoft.com/en-us/windows/win32/dataxchg/wm-dde-initiate`

## Schema

Local schema:

```text
docs/plan/srev-290-gui-chrome-message-only-window-inactive-path.schema.json
```

Contract id:

```text
GUI_CHROME_MESSAGE_ONLY_WINDOW_INACTIVE_PATH
```

## Boundary

```text
caller CreateWindowExW
  -> Gui_CreateWindowExW title/class/parent policy
  -> inactive Dll_ChromeSandbox branch
  -> if revived: WS_CHILD + HWND_MESSAGE topology change
  -> __sys_CreateWindowExW
```

The active owner remains normal `Gui_CreateWindowExW` window creation policy.
The commented branch is historical evidence only. It must not define current
Chrome or DDE behavior without Windows runtime proof.

## Topology

```text
top-level window
  -> participates in broadcast DDE initiation

message-only window via HWND_MESSAGE
  -> receives directed messages
  -> not visible, no z-order, not enumerated
  -> does not receive broadcast messages
```

SREV-084 owns the active DDE proxy ACK payload forwarding contract. This SREV
does not change DDE proxy routing, `Gui_DDE_*` hooks, Chrome detection, window
title/class rewriting, dummy-parent behavior, or `CreateWindowEx` forwarding.

## Logic Risk

The stale comment blended an old Chrome symptom with an inactive topology
change. Reviving the branch would be a behavior change: a top-level window can
participate in broadcast DDE initiation, while a message-only window cannot.
That decision needs a Windows runtime matrix, not an old source comment.

## Fix

Comment-only source clarification. The source now names SREV-290, describes the
branch as inactive, records the official `HWND_MESSAGE` / DDE broadcast
topology, and states that revival requires Windows runtime proof. No
`Dll_ChromeSandbox` predicate, `WS_CHILD` mutation, `HWND_MESSAGE` assignment,
or active `CreateWindowExW` flow changed.

## Acceptance Gate

`docs/plan/check-srev-290.py` validates the draft-07 schema, official
references, inactive source branch, source comment, stale symptom wording
removal, SREV-084 DDE adjacency, unchanged active `Gui_CreateWindowExW` flow,
combined ledger entry, and split ledger fragment.

Runtime gate: Windows Chrome/Chromium sandbox launch matrix with DDE broadcast
observation, hardware-acceleration smoke, top-level and child window creation
capture, and SREV-084 DDE proxy checks before any branch revival.
