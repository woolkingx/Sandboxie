---
kind: srev-ledger-entry
id: SREV-076
title: GUI Console Thread Handoff
status: patched-source-level-after-official-win32-handle-thread-event-wait-shape-and-loc
owner: Sandboxie/core/dll/guicon.c
spec: docs/plan/srev-076-gui-console-thread-handoff.md
schema: docs/plan/srev-076-gui-console-thread-handoff.schema.json
checker: docs/plan/check-srev-076.py
runtime_gate: "console helper startup with normal ready signaling, helper import failure, hidden helper-window creation failure, parent-thread termination, and disabled `Gui_ConsoleHwnd` path"
---
### SREV-076: GUI Console Thread Handoff

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official Win32 handle/thread/event/wait shape and local console-helper handoff analysis; needs Windows console helper runtime proof |
| Evidence | `Sandboxie/core/dll/guicon.c` starts a helper thread for console `WM_DEVICECHANGE` and window-hook notifications. Microsoft documents `OpenThread`, `CreateEvent`, and `CreateThread` as returning handles on success and NULL on failure; `WaitForMultipleObjects` requires a handle array and has undefined behavior if a waited handle is closed while the wait is pending; `CloseHandle` closes open handles but closing a thread handle does not terminate the thread. Before this patch, `Gui_InitConsole2` wrote a three-handle array after `Dll_Alloc` without checking allocation success, mixed parent startup handles with the worker's long-lived main-thread wait handle, and had no explicit cleanup owner for the allocated array or main-thread handle. |
| Data | Allocated worker context, main-thread wait handle, ready event handle, helper thread handle, parent startup wait, worker message wait, and cleanup exits. |
| Schema | `GUI_CONSOLE_THREAD_HANDOFF` says the allocated context must exist before handle slots are written; after successful `CreateThread`, the worker owns the context and main-thread wait handle; the parent owns only the ready event and helper thread handles during startup wait; failed setup and worker exits must close/free owned resources. |
| Topology | `Gui_InitConsole2` allocates worker context, opens the main-thread wait handle, creates a ready event, and crosses the `CreateThread` handoff. The parent waits on local ready-event/helper-thread handles and closes them. The worker signals readiness, waits on the main-thread handle, then closes the main-thread handle and frees its context. |
| Logic Risk | The old three-handle array erased the parent/worker ownership boundary. Freeing or closing everything in the parent would break the worker's pending wait, while leaving the mixed array unowned leaks the allocation and main-thread handle on setup and worker-exit paths. Allocation failure could also crash before any official handle API receives control. |
| Official Shape | `docs/plan/srev-076-gui-console-thread-handoff.md` records Microsoft `OpenThread`, `CreateEvent`, `CreateThread`, `WaitForMultipleObjects`, and `CloseHandle` references. `docs/plan/srev-076-gui-console-thread-handoff.schema.json` records the JSON Schema draft-07 local `GUI_CONSOLE_THREAD_HANDOFF` contract. |
| Fix | `Gui_InitConsole2` now gates context allocation, splits parent-owned startup handles from the worker-owned main-thread wait handle, waits on a local two-handle startup array, and cleans failed setup paths. `Gui_ConsoleThread` now closes the main-thread wait handle and frees the context on import failure, helper-window creation failure, and normal parent-thread termination. |
| Acceptance Gate | `docs/plan/check-srev-076.py` validates the draft-07 schema, official references, allocation gate, parent/worker handle split, removal of the old three-handle wait array, worker cleanup on early exits, and ledger entry; `docs/plan/check-srev-076.sh` is the matrix wrapper. Windows gate: console helper startup with normal ready signaling, helper import failure, hidden helper-window creation failure, parent-thread termination, and disabled `Gui_ConsoleHwnd` path. |
