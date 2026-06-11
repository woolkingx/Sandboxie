---
kind: srev-ledger-entry
id: SREV-090
title: GUI Title RealGetWindowClass Buffer Shape
status: patched-source-level-after-official-realgetwindowclassw-window-style-window-geom
owner: Sandboxie/core/dll/guititle.c
spec: docs/plan/srev-090-guititle-realgetwindowclass-buffer-shape.md
schema: docs/plan/srev-090-guititle-realgetwindowclass-buffer-shape.schema.json
checker: docs/plan/check-srev-090.py
runtime_gate: "Office splash / hidden caption windows still skip title mutation; normal top-level captioned windows still receive the Sandboxie title marker; custom-titlebar windows still skip mutation; `Edit` controls remain excluded; long or unusual class names do not corrupt the stack"
---
### SREV-090: GUI Title RealGetWindowClass Buffer Shape

| Field | Content |
|---|---|
| Severity | [blocker] |
| Status | patched source-level after official `RealGetWindowClassW`, window-style, window-geometry, `GetWindowTextW`, `SetWindowTextW`, and `WM_SETTEXT` shape; needs Windows Office/custom-titlebar/title runtime proof |
| Evidence | `Sandboxie/core/dll/guititle.c` classifies top-level captioned windows before appending the Sandboxie title marker. The Office hidden splash/window skip block calls `RealGetWindowClassW` and then consumes the result through `wcsstr` / `_wcsicmp`. Microsoft documents `RealGetWindowClassW` `cchClassNameMax` as the length in characters of the output buffer. Before this patch, the code passed `sizeof(clsnm) - 1` for `WCHAR clsnm[256]`, advertising a 511-character buffer for a 256-WCHAR local array. |
| Data | Window handle, style bits, window/client geometry, class-name output buffer, Office hidden-window class skip list, `Edit` control exclusion, and title rewrite payload. |
| Schema | `GUITITLE_REALGETWINDOWCLASS_BUFFER_SHAPE` says `RealGetWindowClassW` receives a WCHAR character count, not a byte count; the class-name buffer capacity is passed as `ARRAYSIZE(clsnm)`; the local class string is NUL-terminated before `wcsstr` / `_wcsicmp`; Office hidden-caption skips and the `Edit` exclusion remain the local compatibility classification; title helper consumers keep gating title mutation through `Gui_ShouldCreateTitle` before `GetWindowText` / `SendMessage` / `WM_SETTEXT` paths. |
| Topology | `HWND` crosses into `Gui_ShouldCreateTitle`, through public user32 style/geometry/class queries, into the local Office/`Edit` compatibility gate, then into `Gui_CreateTitleW/A` or `Gui_FixTitleW/A`. Separate GUI owners consume those helpers for create-window, enum, console, and `WM_SETTEXT` message paths only when the gate allows it. |
| Logic Risk | Passing a byte count where the official API expects a character count can let user32 write beyond the stack class buffer. A vague workaround label hid the actual owner boundary: user32 owns class retrieval, but `guititle.c` owns the output buffer size and terminator before local string consumers run. |
| Official Shape | `docs/plan/srev-090-guititle-realgetwindowclass-buffer-shape.md` records Microsoft `RealGetWindowClassW`, `GetWindowLongW`, window styles, `GetWindowRect`, `ClientToScreen`, `GetWindowTextW`, `SetWindowTextW`, and `WM_SETTEXT` references. `docs/plan/srev-090-guititle-realgetwindowclass-buffer-shape.schema.json` records the JSON Schema draft-07 local `GUITITLE_REALGETWINDOWCLASS_BUFFER_SHAPE` contract. |
| Fix | `Gui_ShouldCreateTitle` now passes `ARRAYSIZE(clsnm)` to `RealGetWindowClassW`, defensively clamps oversized return values, writes a local NUL terminator before string consumers, and removes the stale anonymous `$Workaround$` comment. |
| Acceptance Gate | `docs/plan/check-srev-090.py` validates the draft-07 schema, official Win32 references, `ARRAYSIZE(clsnm)` use, defensive NUL termination, stale byte-count call removal, Office class skip list preservation, `Edit` exclusion preservation, helper-consumer title-rewrite topology preservation, and ledger entry; `docs/plan/check-srev-090.sh` is the matrix wrapper. Windows gate: Office splash / hidden caption windows still skip title mutation; normal top-level captioned windows still receive the Sandboxie title marker; custom-titlebar windows still skip mutation; `Edit` controls remain excluded; long or unusual class names do not corrupt the stack. |
