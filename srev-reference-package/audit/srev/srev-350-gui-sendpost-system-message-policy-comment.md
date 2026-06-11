# SREV-350: GUI Send/Post System Message Policy Comment

| Field | Content |
|---|---|
| Stage | schema -> boundary -> topology -> verify |
| Input artifact | `Sandboxie/core/svc/GuiServer.cpp`, SREV-347, SREV-293, and Microsoft window-message documentation |
| Output artifact | Comment-only source patch, draft-07 schema, checker, and ledger fragment |
| Owner | `GuiServer::AllowSendPostMessage` system-message deny policy |
| Acceptance gate | Targeted checker validates official references, message denylist preservation, Explorer `WM_USER` policy adjacency, stale result-only wording removal, and ledger fragment |

## Data

`SendPostMessageSlave` brokers sandboxed `SendMessage`, `PostMessage`,
`SendMessageTimeout`, and `SendNotifyMessage` requests to windows outside the
sandbox. After `OpenWinClass` and integrity checks, it calls
`AllowSendPostMessage` to decide whether a specific message may cross into the
host window.

`AllowSendPostMessage` already has three layers:

```text
OpenAllWinClasses -> allow
input messages -> allow
selected system messages below WM_USER -> deny
Explorer WM_USER and input special cases -> allow/deny by target class
```

Before this SREV, the system-message denylist comment described the denied
messages by possible outcomes such as hiding, closing, or crashing windows. The
behavior was useful, but the comment did not name the semantic owner: this is a
cross-sandbox lifecycle, shutdown, notification, and shell-control message
policy.

## Official Shape

Microsoft documents Windows messages as values sent or posted to a window
procedure with message-specific `wParam` and `lParam` meanings. `WM_CLOSE` asks
a window or application to terminate, and the default window procedure destroys
the window. `WM_QUERYENDSESSION` is part of the system shutdown/session-end
protocol and affects whether a session ends. `WM_QUIT` is not a window
procedure message and should be produced with `PostQuitMessage`, not posted to
a window. `WM_SYSCOMMAND` carries system-menu/window commands such as
`SC_CLOSE`, minimize, maximize, move, and monitor power. `WM_NOTIFY` carries a
pointer to notification data.

Official references:

- `https://learn.microsoft.com/en-us/windows/win32/winmsg/about-messages-and-message-queues`
- `https://learn.microsoft.com/en-us/windows/win32/winmsg/wm-close`
- `https://learn.microsoft.com/en-us/windows/win32/shutdown/wm-queryendsession`
- `https://learn.microsoft.com/en-us/windows/win32/winmsg/wm-quit`
- `https://learn.microsoft.com/en-us/windows/win32/menurc/wm-syscommand`
- `https://learn.microsoft.com/en-us/windows/win32/controls/wm-notify`

## Boundary

The sandbox may synthesize user-input-shaped messages for host windows when
policy allows it. It must not treat lifecycle, shutdown, notification pointer,
or shell-control messages as ordinary input just because the target window is
visible and addressable.

`AllowSendPostMessage` owns only the cross-sandbox message policy decision. The
actual message semantics still belong to the target window procedure and to
Windows.

## Topology

```text
sandboxed sender
  -> Gui_SendPostMessageCommon
  -> GUI_SEND_POST_MESSAGE
  -> SendPostMessageSlave
  -> CheckWindowAccessible / integrity gate
  -> AllowSendPostMessage
  -> system-message denylist below WM_USER
  -> allowed messages call PostMessage/SendMessage/SendMessageTimeout
```

## Logic Risk

If the denylist is framed only as a historical workaround for bad effects,
future edits may remove entries as "too broad" without checking the official
message semantics. Messages such as `WM_QUERYENDSESSION`, `WM_QUIT`,
`WM_SYSCOMMAND`, and `WM_NOTIFY` are not equivalent to input messages: they
carry session, process, shell, or pointer-data semantics.

## Fix

The source comment now names SREV-350 and describes the denylist as
cross-sandbox lifecycle, shutdown, notification, and shell-control message
policy. No message ids, `OpenAllWinClasses` behavior, input-message allow rule,
Explorer `WM_USER` class exceptions, or reply/error behavior changed.

## Acceptance Gate

`docs/plan/check-srev-350.py` validates the draft-07 schema, official
references, `AllowSendPostMessage` denylist preservation, input-message allow
rule, Explorer `WM_USER` policy adjacency, new topology comment, stale
result-only wording removal, combined ledger entry, and split ledger fragment.

Runtime gate: none for this comment-only source clarification. Existing
Windows runtime coverage for message policy remains required before changing
message ids or target-window class exceptions.
