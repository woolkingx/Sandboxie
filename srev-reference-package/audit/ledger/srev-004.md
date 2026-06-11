---
kind: srev-ledger-entry
id: SREV-004
title: Taskbar AppUserModelID Hook Trades Crash For Leak
status: patched-source-level-after-official-appusermodelid-peb-posture-and-local-workaro
owner: "Sandboxie/core/dll/taskbar.c:384-392"
spec: docs/plan/srev-004-taskbar-appid-process-parameters.md
schema: docs/plan/srev-004-taskbar-appid-process-parameters.schema.json
checker: docs/plan/check-srev-004.sh
runtime_gate: "taskbar AppUserModelID still works, the WindowTitle crash does not return, and later process-parameter reads see the original `0x5000` bits"
---
### SREV-004: Taskbar AppUserModelID Hook Trades Crash For Leak

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official AppUserModelID/PEB posture and local workaround analysis; needs Windows taskbar/runtime proof |
| Evidence | `Sandboxie/core/dll/taskbar.c:384-392` says clearing `ProcessParms->WindowFlags &= ~0x5000` avoids a crash but leaks `WindowTitle`. |
| Data | PEB `RTL_USER_PROCESS_PARAMETERS.WindowFlags` and `WindowTitle` ownership. |
| Schema | Windows owns the process parameter lifetime and flag semantics; manual flag mutation is undocumented internal-state surgery. |
| Topology | Hooked shell/taskbar API crosses into process parameter internals. |
| Logic Risk | Leak is known; flag semantics may drift across Windows versions. |
| Official Shape | `docs/plan/srev-004-taskbar-appid-process-parameters.md` records Microsoft `SetCurrentProcessExplicitAppUserModelID`, AppUserModelID, PEB, and `RTL_USER_PROCESS_PARAMETERS` posture. |
| Fix | The workaround now saves `WindowFlags`, clears only the local `0x5000` mask during the real Shell API call, then restores the saved mask bits while preserving any other flag changes from the real API. |
| Acceptance Gate | `docs/plan/check-srev-004.sh` proves the `WindowFlags` mutation is scoped around the Shell API call instead of being permanent. Windows gate: taskbar AppUserModelID still works, the WindowTitle crash does not return, and later process-parameter reads see the original `0x5000` bits. |
