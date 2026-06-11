---
kind: srev-ledger-entry
id: SREV-350
title: GUI Send/Post System Message Policy Comment
status: patched-comment-topology-after-official-window-message-review-no-behavior-change
owner: Sandboxie/core/svc/GuiServer.cpp
spec: docs/plan/srev-350-gui-sendpost-system-message-policy-comment.md
schema: docs/plan/srev-350-gui-sendpost-system-message-policy-comment.schema.json
checker: docs/plan/check-srev-350.py
runtime_gate: none for comment-only clarification; Windows runtime proof required before behavior changes
---

### SREV-350: GUI Send/Post System Message Policy Comment

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | patched comment/topology after official window-message review; no behavior change |
| Evidence | `SendPostMessageSlave` checks `OpenWinClass`, integrity level, and then calls `AllowSendPostMessage` before sending or posting messages to windows outside the sandbox. `AllowSendPostMessage` allows `OpenAllWinClasses`, input-shaped messages, and then denies selected system messages below `WM_USER` before applying Explorer `WM_USER` class exceptions. Microsoft documents `WM_CLOSE`, `WM_QUERYENDSESSION`, `WM_QUIT`, `WM_SYSCOMMAND`, and `WM_NOTIFY` as message-specific contracts carrying lifecycle, shutdown, system-command, or pointer-data semantics. |
| Data | `SendPostMessageSlave`, `AllowSendPostMessage`, `GUI_SEND_POST_MESSAGE_REQ.msg`, `OpenWinClass`, integrity checks, `SBIE_FLAG_OPEN_ALL_WIN_CLASS`, input messages, system-message denylist below `WM_USER`, Explorer target classes, `WM_CLOSE`, `WM_QUERYENDSESSION`, `WM_QUIT`, `WM_SYSCOMMAND`, and `WM_NOTIFY`. |
| Schema | `GUI_SENDPOST_SYSTEM_MESSAGE_POLICY_COMMENT` says `AllowSendPostMessage` owns the cross-sandbox send/post message policy decision; input-shaped messages are allowed before the system-message denylist; selected messages below `WM_USER` are denied because they carry lifecycle, shutdown, notification, or shell-control semantics; Explorer `WM_USER` class exceptions remain a separate compatibility policy; this SREV changes comments and proof only and preserves the message id denylist. |
| Topology | `sandboxed sender -> Gui_SendPostMessageCommon -> GUI_SEND_POST_MESSAGE -> SendPostMessageSlave -> CheckWindowAccessible / integrity gate -> AllowSendPostMessage -> system-message denylist below WM_USER -> allowed messages call PostMessage/SendMessage/SendMessageTimeout`. |
| Logic Risk | If the denylist is framed only as a historical workaround for bad effects, future edits may remove entries as "too broad" without checking the official message semantics. Messages such as `WM_QUERYENDSESSION`, `WM_QUIT`, `WM_SYSCOMMAND`, and `WM_NOTIFY` are not equivalent to input messages. |
| Official Shape | Microsoft documents Windows messages as values delivered to window procedures with message-specific `wParam` and `lParam`; `WM_CLOSE` asks a window/application to terminate; `WM_QUERYENDSESSION` participates in shutdown/session-end; `WM_QUIT` is not a window-procedure message and should be produced by `PostQuitMessage`; `WM_SYSCOMMAND` carries system-menu and shell-control commands such as `SC_CLOSE`; and `WM_NOTIFY` carries notification data through `lParam`. |
| Fix | Comment-only source clarification. The source now names SREV-350 and describes the denylist as cross-sandbox lifecycle, shutdown, notification, and shell-control message policy. No message ids, `OpenAllWinClasses` behavior, input-message allow rule, Explorer `WM_USER` class exceptions, or reply/error behavior changed. |
| Acceptance Gate | `docs/plan/check-srev-350.py` validates the draft-07 schema, official references, `AllowSendPostMessage` denylist preservation, input-message allow rule, Explorer `WM_USER` policy adjacency, new topology comment, stale result-only wording removal, combined ledger entry, and split ledger fragment; `docs/plan/check-srev-350.sh` is the targeted wrapper. Runtime gate: none for this comment-only source clarification. Existing Windows runtime coverage for message policy remains required before changing message ids or target-window class exceptions. |
