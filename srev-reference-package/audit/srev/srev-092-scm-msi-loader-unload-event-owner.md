# SREV-092: SCM MSI Loader Unload Event Owner

## Data

`Sandboxie/core/dll/scm_msi.c` owns the MSI-specific DLL hooks and the client-side
named event that tells the sandboxed MSI server another process is using it.
The comment-admitted shape is:

```text
msi.dll load callback
msi.dll unload callback state
Scm_MsiDll module init function
SBIE_WindowsInstallerInUse named event
MSI server waiter that exits when the named event disappears
MSIHANDLE close functions
```

## Official Shape

Microsoft documents `LdrRegisterDllNotification` as registering a callback for
DLL load notification and warns that the function may change or be removed
without notice.

Microsoft documents `LdrDllNotification` as receiving
`LDR_DLL_NOTIFICATION_REASON_LOADED` and
`LDR_DLL_NOTIFICATION_REASON_UNLOADED`. The unload reason points to
`LDR_DLL_UNLOADED_NOTIFICATION_DATA`. Microsoft also warns that it is unsafe for
the notification callback to call functions in any module other than itself.

Microsoft documents `MsiCloseHandle` as closing one open installation handle and
requiring that it be called from the same thread that created that handle.
Microsoft documents `MsiCloseAllHandles` as a diagnostic function that closes
handles allocated by the current thread and should not be used for cleanup.

Microsoft documents named event objects as kernel synchronization objects that
can be opened by name from other processes. `CreateEventW` creates or opens a
named event and `CloseHandle` closes a handle; the event object is destroyed
when its last handle has been closed.

```text
https://learn.microsoft.com/en-us/windows/win32/devnotes/ldrregisterdllnotification
https://learn.microsoft.com/en-us/windows/win32/devnotes/ldrdllnotification
https://learn.microsoft.com/en-us/windows/win32/api/msi/nf-msi-msiclosehandle
https://learn.microsoft.com/en-us/windows/win32/api/msi/nf-msi-msicloseallhandles
https://learn.microsoft.com/en-us/windows/win32/sync/event-objects
https://learn.microsoft.com/en-us/windows/win32/api/synchapi/nf-synchapi-createeventw
https://learn.microsoft.com/en-us/windows/win32/api/handleapi/nf-handleapi-closehandle
```

## Schema

Local schema:

```text
docs/plan/srev-092-scm-msi-loader-unload-event-owner.schema.json
```

The event-owner contract is:

```text
msi.dll load may create the SBIE_WindowsInstallerInUse named event
loader unload notifications are recorded by the Ldr layer; sub-module init functions are called on load and unload_func is optional
Scm_MsiDll(NULL) unload cleanup releases the process event hold created on msi.dll load
MsiCloseHandle closes a per-thread installer handle and is not a proven last-MSI-session owner
MsiCloseAllHandles is diagnostic and must not become the cleanup owner
the MSI server waiter exits only when the named in-use event no longer opens
source path now releases the process event hold on msi.dll unload
runtime capture must prove the last-user edge across MSI module lifetime,
installer handles, custom actions, and MSIServer process lifetime before any
event-release behavior change
```

## Topology

```text
msi.dll load
  -> Ldr_MyDllCallbackNew(load)
  -> Scm_MsiDll(ImageBase)
  -> CreateEvent(SBIE_WindowsInstallerInUse)
  -> sandboxed MSI server waiter opens event by name
  -> MSI server exits when no process keeps the named event alive
```

Current unload topology:

```text
msi.dll unload
  -> Ldr_MyDllCallbackNew(unload)
  -> dll->unload_func(NULL) for msi.dll
  -> Scm_MsiDll(NULL)
  -> CloseHandle(Msi_ServerInUseEvent)
  -> dll->state = 0 and SbieDll_UnHookModule(ImageBase)
```

Potential MSI handle topology:

```text
MsiCloseHandle(MSIHANDLE)
  -> closes one installer handle owned by the creating thread
  -> does not prove all MSI work in this process is finished
```

## Logic Risk

The old comment named a real gap but suggested the wrong next owner. The loader
does expose unload notifications, so the legal owner is the module lifetime
edge, not an MSI handle-close edge. The source now gives `Ldr_Dlls` an optional
`unload_func` and wires only `msi.dll` to `Scm_MsiDll(NULL)`.

Binding `Msi_ServerInUseEvent` to `MsiCloseHandle` is also not a valid shape by
itself. `MsiCloseHandle` is per-handle and per-thread; it does not prove that the
process has no remaining installer handles, no active install transaction, and no
MSI custom action still using the service.

## Runtime Capture Matrix

The Windows gate is not "MSI install still works". It must prove the real
last-user edge before Sandboxie changes event release behavior.

Required dimensions:

- Windows builds: supported Windows 10 and Windows 11 releases, with build
  number and architecture recorded.
- MSI entry path: install, repair, uninstall, advertised repair, and custom
  action process.
- Client process shape: one client process, multiple concurrent client
  processes, nested custom action process, and early client crash.
- Module lifetime: `msi.dll` load notification, unload notification, and
  Sandboxie `Ldr_MyDllCallbackNew` load/unload state transition.
- Event lifetime: `CreateEvent(SBIE_WindowsInstallerInUse)`, open waiter
  success/failure, last handle close, and `CloseHandle(Msi_ServerInUseEvent)`.
- MSI handle state: `MsiOpenPackage`, `MsiOpenProduct`, `MsiGetActiveDatabase`,
  `MsiDatabaseOpenView`, `MsiViewFetch`, `MsiCloseHandle`, and
  `MsiCloseAllHandles` diagnostic readback where safe.
- Server lifetime: sandboxed MSIServer start, wait-loop polling,
  last-user exit, and non-exit while any live installer handle or custom action
  remains.

Negative controls:

- `MsiCloseHandle` on one handle while another same-thread handle remains open;
- `MsiCloseHandle` on one handle while another thread still owns an MSI handle;
- `MsiCloseAllHandles` returning a diagnostic count without becoming cleanup
  owner;
- `msi.dll` unload notification while a custom action or installer transaction
  is still active;
- failed MSI load or failed event creation;
- non-MSI process loading and unloading unrelated DLLs.

## Fix

Source-level event-release path: `Ldr_Dlls` now has an optional `unload_func`
slot. The `msi.dll` entry wires that slot to `Scm_MsiDll`, and
`Ldr_MyDllCallbackNew(unload)` calls `dll->unload_func(NULL)` before clearing the
module state. `Scm_MsiDll(NULL)` closes `Msi_ServerInUseEvent` and clears the
handle. `MsiCloseHandle` remains explicitly outside the event-owner path.

## Acceptance Gate

`docs/plan/check-srev-092.py` validates the draft-07 schema, official loader/MSI
handle/event references, `Ldr_Dlls` `msi.dll -> Scm_MsiDll` load registration,
the optional unload callback slot, `msi.dll -> Scm_MsiDll(NULL)` unload routing,
named-event creation, event close/clear on unload, MSI server waiter behavior,
concrete runtime capture matrix, and ledger entry.

Windows runtime proof remains required: run a Windows MSI runtime matrix that
proves the true last-user edge for client MSI processes across module lifetime,
installer handles, custom actions, and MSIServer lifetime. It must verify that
the sandboxed MSIServer exits after the last real MSI user without exiting while
custom actions or installer handles remain active.

## Shared Runtime Capture Evidence

This SREV shares a user-mode lifecycle runtime evidence contract with SREV-322:

```text
docs/plan/srev-092-322-user-lifecycle-runtime-capture-playbook.md
docs/plan/srev-092-322-user-lifecycle-runtime-capture.schema.json
docs/plan/check-srev-092-322-user-lifecycle-runtime-capture.sh
```

The machine feature path for this entry is `msi-last-user-event`.

Windows gate: validate captured MSI lifecycle records against
`docs/plan/srev-092-322-user-lifecycle-runtime-capture.schema.json` before any
event-release or MSIServer lifetime behavior change.
