# SREV-076: GUI Console Thread Handoff

## Data

`Sandboxie/core/dll/guicon.c` starts a helper thread for console
`WM_DEVICECHANGE` and window-hook notifications. The helper thread waits on the
main thread handle so it can exit when the main thread terminates.

The relevant data nodes are:

```text
allocated HANDLE context
main thread wait handle
ready event handle
helper thread handle
parent startup wait
worker message wait
context cleanup
```

## Official Shape

Microsoft documents `OpenThread`, `CreateEvent`, and `CreateThread` as returning
handles on success and NULL on failure. `WaitForMultipleObjects` receives an
array of handles and its behavior is undefined if a waited handle is closed
while the wait is pending. `CloseHandle` closes open object handles, and closing
a thread handle does not terminate the associated thread.

```text
https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-openthread
https://learn.microsoft.com/en-us/windows/win32/api/synchapi/nf-synchapi-createeventw
https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-createthread
https://learn.microsoft.com/en-us/windows/win32/api/synchapi/nf-synchapi-waitformultipleobjects
https://learn.microsoft.com/en-us/windows/win32/api/handleapi/nf-handleapi-closehandle
```

## Schema

Local schema:

```text
docs/plan/srev-076-gui-console-thread-handoff.schema.json
```

The handoff contract is:

```text
the allocated context must exist before handle slots are written
the worker owns the main-thread wait handle after CreateThread succeeds
the parent owns only the ready-event and helper-thread handles during startup wait
the parent must not close a handle that the worker still waits on
failed setup must close opened handles and free the context
worker exits must close the main-thread wait handle and free the context
```

## Topology

```text
Gui_InitConsole2 -> allocate worker context -> open main-thread wait handle
Gui_InitConsole2 -> create ready event -> create helper thread
parent -> wait on ready event or helper-thread exit -> close parent-owned handles
worker -> signal ready event -> wait on main-thread handle -> close/free worker-owned context
```

The parent/worker boundary is the `CreateThread` handoff. After that boundary,
the worker owns the context and the main-thread wait handle.

## Logic Risk

Before this patch, one three-handle array mixed parent startup handles with the
worker's long-lived wait handle. Allocation was not checked before the array was
written. The array and main-thread handle also had no explicit lifetime exit.
Closing or freeing everything in the parent would be wrong because the worker
continues to wait on the main-thread handle. Leaving everything unowned leaks
the allocation and handle when setup or worker exit paths run.

## Fix

`Gui_InitConsole2` now allocates a two-slot worker context, checks allocation,
and uses local parent-owned handles for the ready-event/helper-thread startup
wait. Once `CreateThread` succeeds, the worker owns the context and
main-thread wait handle. `Gui_ConsoleThread` frees that context and closes the
main-thread handle on every early exit and normal exit. Failed setup paths clean
up in the parent.

## Acceptance Gate

`docs/plan/check-srev-076.py` validates the draft-07 schema, official handle and
wait references, allocation gate, parent/worker handle split, removal of the
old three-handle wait array, worker cleanup on early exits, and ledger entry.

Windows gate: console helper startup with normal ready signaling, helper import
failure, hidden helper-window creation failure, parent-thread termination, and
disabled `Gui_ConsoleHwnd` path.
