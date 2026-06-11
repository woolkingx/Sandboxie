# SREV-292: GuiCon Console Taskbar Inactive Edge

## Stage Gate

| Field | Value |
|---|---|
| Stage | schema -> boundary -> topology -> verify |
| Input artifact | `Sandboxie/core/dll/guicon.c`, `Sandboxie/core/dll/taskbar.c`, SREV-004, SREV-076, SREV-241, Microsoft AppUserModelID and window property store references |
| Output artifact | Source comment owner, draft-07 schema, targeted checker, ledger fragment |
| Owner | `Gui_ConsoleThread` inactive console AppUserModelID branch |
| Acceptance gate | Targeted checker validates source comment, inactive branch shape, taskbar owner adjacency, SREV-004/SREV-076/SREV-241 adjacency, stale symptom wording removal, and ledger fragment |

## Data

`Gui_ConsoleThread` contains an inactive branch inside the helper message loop:

```c
//if (Gui_ConsoleHwnd && Dll_InitComplete) {
//
//    Taskbar_SetWindowAppUserModelId(Gui_ConsoleHwnd);
//    Gui_ConsoleHwnd = NULL;
//}
```

The old comment said the branch caused `git.exe` to hang and that Jump Lists
for a console process were pointless. The behavior is already inactive, but the
comment mixed an application symptom with a Shell/AppUserModelID topology
decision and did not name the owner boundary.

## Official Shape

Microsoft documents AppUserModelIDs as taskbar identities used to associate
processes, files, and windows with an application, including taskbar grouping
and Jump List contents.

Microsoft documents `SHGetPropertyStoreForWindow` as the API for retrieving a
window property store so an application can set an explicit AppUserModelID in
`System.AppUserModel.ID`.

Microsoft documents `SetCurrentProcessExplicitAppUserModelID` as a process
AppUserModelID API that must be called during initial startup before UI or Jump
List manipulation.

Official references:

- `https://learn.microsoft.com/en-us/windows/win32/shell/appids`
- `https://learn.microsoft.com/en-us/windows/win32/api/shellapi/nf-shellapi-shgetpropertystoreforwindow`
- `https://learn.microsoft.com/en-us/windows/win32/api/shobjidl_core/nf-shobjidl_core-setcurrentprocessexplicitappusermodelid`

## Schema

Local schema:

```text
docs/plan/srev-292-guicon-console-taskbar-inactive-edge.schema.json
```

Contract id:

```text
GUICON_CONSOLE_TASKBAR_INACTIVE_EDGE
```

## Boundary

```text
Gui_ConsoleThread
  -> helper window message pump
  -> inactive Gui_ConsoleHwnd AppUserModelID branch
  -> if revived: Taskbar_SetWindowAppUserModelId(HWND)
  -> taskbar.c SHGetPropertyStoreForWindow / property rewrite owner
```

`Gui_ConsoleThread` owns helper-window message pumping and parent-thread
termination wait. It does not own Shell taskbar identity policy, process
AppUserModelID state, window property-store rewriting, or Jump List behavior.

## Topology

```text
Gui_InitConsole2
  -> SREV-076 helper thread handoff
  -> Gui_ConsoleThread helper window / message pump
  -> inactive console taskbar edge

normal visible windows
  -> gui.c / guidlg.c callers
  -> Taskbar_SetWindowAppUserModelId
  -> taskbar.c property store rewriting
```

SREV-004 owns the process AppUserModelID / PEB workaround. SREV-241 owns the
taskbar header and caller topology. SREV-076 owns the console helper thread
handoff and cleanup.

## Logic Risk

The old wording could lead future work to revive or delete the branch based on
one application symptom instead of the Shell taskbar topology. A console helper
message loop should not become a taskbar policy owner by accident. If the edge
is revived, it must be tested as a Windows taskbar/window-property behavior
change and as a console/git compatibility matrix.

## Fix

Comment-only source clarification. The source now names SREV-292, records the
branch as an inactive console AppUserModelID experiment, separates console
helper message pumping from taskbar window-property rewriting, and points branch
revival to Windows console/git runtime proof plus SREV-004/SREV-241 taskbar
gates. No message loop, `Gui_ConsoleHwnd` gate, `Dll_InitComplete` gate,
`Taskbar_SetWindowAppUserModelId` call, or `Gui_ConsoleHwnd = NULL` statement
changed.

## Acceptance Gate

`docs/plan/check-srev-292.py` validates the draft-07 schema, official
references, source comment, inactive branch, stale symptom wording removal,
taskbar implementation adjacency, SREV-004/SREV-076/SREV-241 adjacency,
combined ledger entry, and split ledger fragment.

Runtime gate: Windows console helper smoke, git-for-Windows console launch
smoke, taskbar grouping / Jump List observation, and existing SREV-004/SREV-241
taskbar gates before any branch revival.
