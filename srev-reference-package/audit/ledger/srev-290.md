---
kind: srev-ledger-entry
id: SREV-290
title: GUI Chrome Message-Only Window Inactive Path
status: patched-comment-topology-after-official-createwindowex-message-only-and-dde-review-no-behavior-change
owner: Sandboxie/core/dll/gui.c
spec: docs/plan/srev-290-gui-chrome-message-only-window-inactive-path.md
schema: docs/plan/srev-290-gui-chrome-message-only-window-inactive-path.schema.json
checker: docs/plan/check-srev-290.py
runtime_gate: Windows Chrome Chromium sandbox launch matrix with DDE broadcast observation hardware acceleration smoke top-level and child window creation capture and SREV-084 DDE proxy checks before any branch revival
---

### SREV-290: GUI Chrome Message-Only Window Inactive Path

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | patched comment/topology after official CreateWindowEx, message-only window, and DDE review; no behavior change |
| Evidence | `Gui_CreateWindowExW` contains an inactive `Dll_ChromeSandbox` branch that would set `WS_CHILD` and `hWndParent = HWND_MESSAGE`. The old comment described an old Chrome DDE broadcast symptom and said the branch is no longer used because of Chrome hardware acceleration impact. The behavior is already inactive, but the comment could still drive an unsafe branch revival. |
| Data | `Gui_CreateWindowExW`, `Dll_ChromeSandbox`, `dwStyle`, `WS_CHILD`, `hWndParent`, `HWND_MESSAGE`, title rewrite, class rewrite, parent validity policy, `__sys_CreateWindowExW`, DDE broadcast initiation, and SREV-084 active DDE proxy behavior. |
| Schema | `GUI_CHROME_MESSAGE_ONLY_WINDOW_INACTIVE_PATH` says `Gui_CreateWindowExW` owns active title/class/parent and `CreateWindowExW` forwarding policy; the `Dll_ChromeSandbox` `WS_CHILD` / `HWND_MESSAGE` branch remains inactive; `HWND_MESSAGE` creates message-only windows that do not receive broadcast messages; DDE initiation may broadcast `WM_DDE_INITIATE` to top-level windows; branch revival requires Windows runtime proof and must not be driven by stale symptom wording; SREV-084 owns active DDE proxy ACK payload forwarding; this SREV changes comments and proof only. |
| Topology | `top-level window -> participates in broadcast DDE initiation`; `message-only window via HWND_MESSAGE -> receives directed messages -> not visible, no z-order, not enumerated -> does not receive broadcast messages`. Active source flow remains `Gui_CreateWindowExW -> title/class/parent policy -> __sys_CreateWindowExW`. |
| Logic Risk | Reviving the branch would be a behavior change. A top-level window can participate in broadcast DDE initiation, while a message-only window cannot. That decision needs a Windows runtime matrix, not an old source comment. |
| Official Shape | Microsoft documents `CreateWindowExW` and `hWndParent`, message-only windows created through `HWND_MESSAGE`, and DDE initiation through `WM_DDE_INITIATE` broadcast to top-level windows. |
| Fix | Comment-only source clarification. The source now names SREV-290, describes the branch as inactive, records the official `HWND_MESSAGE` / DDE broadcast topology, and states that revival requires Windows runtime proof. No `Dll_ChromeSandbox` predicate, `WS_CHILD` mutation, `HWND_MESSAGE` assignment, or active `CreateWindowExW` flow changed. |
| Acceptance Gate | `docs/plan/check-srev-290.py` validates the draft-07 schema, official references, inactive source branch, source comment, stale symptom wording removal, SREV-084 DDE adjacency, unchanged active `Gui_CreateWindowExW` flow, combined ledger entry, and split ledger fragment; `docs/plan/check-srev-290.sh` is the targeted wrapper. Runtime gate: Windows Chrome/Chromium sandbox launch matrix with DDE broadcast observation, hardware-acceleration smoke, top-level and child window creation capture, and SREV-084 DDE proxy checks before any branch revival. |
