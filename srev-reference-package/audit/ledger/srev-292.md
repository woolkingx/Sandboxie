---
kind: srev-ledger-entry
id: SREV-292
title: GuiCon Console Taskbar Inactive Edge
status: patched-comment-topology-after-official-appusermodelid-window-property-store-review-no-behavior-change
owner: Sandboxie/core/dll/guicon.c
spec: docs/plan/srev-292-guicon-console-taskbar-inactive-edge.md
schema: docs/plan/srev-292-guicon-console-taskbar-inactive-edge.schema.json
checker: docs/plan/check-srev-292.py
runtime_gate: Windows console helper smoke git-for-Windows console launch smoke taskbar grouping Jump List observation and SREV-004 SREV-241 taskbar gates before any branch revival
---

### SREV-292: GuiCon Console Taskbar Inactive Edge

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | patched comment/topology after official AppUserModelID and window property-store review; no behavior change |
| Evidence | `Gui_ConsoleThread` contains an inactive `Gui_ConsoleHwnd && Dll_InitComplete` branch that would call `Taskbar_SetWindowAppUserModelId(Gui_ConsoleHwnd)` and clear `Gui_ConsoleHwnd`. The old comment said the branch caused `git.exe` to hang and that Jump Lists for a console process were pointless. The behavior is already inactive, but the comment mixed an application symptom with a Shell/AppUserModelID topology decision. |
| Data | `Gui_ConsoleThread`, helper window message loop, `Gui_ConsoleHwnd`, `Dll_InitComplete`, `Taskbar_SetWindowAppUserModelId`, `Taskbar_SetProcessAppUserModelId`, `SHGetPropertyStoreForWindow`, `PKEY_AppUserModel_ID`, AppUserModelID, Jump List, SREV-004, SREV-076, and SREV-241. |
| Schema | `GUICON_CONSOLE_TASKBAR_INACTIVE_EDGE` says `Gui_ConsoleThread` owns helper-window message pumping and parent-thread wait behavior; the `Gui_ConsoleHwnd` `Taskbar_SetWindowAppUserModelId` branch remains inactive; `taskbar.c` owns Shell AppUserModelID and window property-store rewriting; SREV-004 owns process AppUserModelID process-parameter workaround gates; SREV-076 owns console helper thread handoff and cleanup; SREV-241 owns taskbar caller topology; branch revival requires Windows console/git/taskbar runtime proof; this SREV changes comments and proof only. |
| Topology | `Gui_InitConsole2 -> SREV-076 helper thread handoff -> Gui_ConsoleThread helper window / message pump -> inactive console taskbar edge`; `normal visible windows -> gui.c / guidlg.c callers -> Taskbar_SetWindowAppUserModelId -> taskbar.c property store rewriting`. |
| Logic Risk | A console helper message loop should not become a taskbar policy owner by accident. Reviving the branch would cross into Shell taskbar/window-property behavior and must be tested as a Windows taskbar and git-for-Windows console compatibility change, not justified by stale symptom wording. |
| Official Shape | Microsoft documents AppUserModelIDs as taskbar identities for processes, files, and windows, including grouping and Jump List contents. Microsoft documents `SHGetPropertyStoreForWindow` as the window property-store API used to set window AppUserModelIDs. Microsoft documents `SetCurrentProcessExplicitAppUserModelID` as a process AppUserModelID API that should run during startup before UI or Jump List manipulation. |
| Fix | Comment-only source clarification. The source now names SREV-292, records the branch as an inactive console AppUserModelID experiment, separates console helper message pumping from taskbar window-property rewriting, and points branch revival to Windows console/git runtime proof plus SREV-004/SREV-241 taskbar gates. No message loop, `Gui_ConsoleHwnd` gate, `Dll_InitComplete` gate, `Taskbar_SetWindowAppUserModelId` call, or `Gui_ConsoleHwnd = NULL` statement changed. |
| Acceptance Gate | `docs/plan/check-srev-292.py` validates the draft-07 schema, official references, source comment, inactive branch, stale symptom wording removal, taskbar implementation adjacency, SREV-004/SREV-076/SREV-241 adjacency, combined ledger entry, and split ledger fragment; `docs/plan/check-srev-292.sh` is the targeted wrapper. Runtime gate: Windows console helper smoke, git-for-Windows console launch smoke, taskbar grouping / Jump List observation, and existing SREV-004/SREV-241 taskbar gates before any branch revival. |
