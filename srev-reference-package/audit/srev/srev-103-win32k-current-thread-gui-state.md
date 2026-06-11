# SREV-103: Win32k Current Thread GUI State

## Data

`Sandboxie/core/drv/syscall_win32.c` owns the win32k syscall table import and
the `Syscall_Api_Invoke32` dispatch path used when a sandboxed process asks the
driver to invoke a win32k syscall while temporarily using the less restricted
thread token.

The uncovered comment was attached to this path:

```text
todo: call KiConvertToGuiThread() or PsConvertToGuiThread()
```

The local call chain is:

```text
Syscall_Api_Invoke
  -> Syscall_Api_Invoke32 for syscall indexes with 0x1000 set
  -> Thread_SetThreadToken when policy allows
  -> optional handler1_func
  -> direct Syscall_Invoke32
  -> Sbie_InvokeSyscall_asm(entry->ntos_func or entry->ntos_func2)
  -> Thread_ClearThreadToken
```

Before this SREV, the non-handler path used
`PsGetProcessWin32Process(PsGetCurrentProcess())` as the guard before direct
win32k dispatch.

## Official Shape

Microsoft documents `IsGUIThread` as a user-mode function that determines
whether the calling thread is already a GUI thread and can optionally convert
that calling thread when `bConvert` is `TRUE`.

Microsoft documents desktop connection as thread-owned: after a process connects
to a window station, the system assigns a desktop to the thread making the
connection. The rules mention `SetThreadDesktop`, inherited desktop state, and
fallback to a default desktop for the window station.

Microsoft documents `PsGetCurrentThread` as returning the executive thread
object for the currently executing thread.

Microsoft's public kernel DDI index lists documented driver-callable kernel
routines, including ordinary `Ps*` and `Ke*` thread routines. `PsConvertToGuiThread`
and `KiConvertToGuiThread` are not documented WDK DDIs in the searched Microsoft
Learn surface, so this driver path must not turn the stale todo into a direct
private call without a version-gated runtime proof.

```text
https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-isguithread
https://learn.microsoft.com/en-us/windows/win32/winstation/thread-connection-to-a-desktop
https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-psgetcurrentthread
https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/_kernel/
```

## Schema

Local schema:

```text
docs/plan/srev-103-win32k-current-thread-gui-state.schema.json
```

The win32k current-thread GUI-state contract is:

```text
IsGUIThread documents GUI state and optional conversion for the calling thread
Thread Connection to a Desktop assigns a desktop to the thread making the connection
PsGetCurrentThread returns the executive thread object for the current thread
PsConvertToGuiThread and KiConvertToGuiThread are not documented WDK DDIs and must not be called directly from this driver path
Syscall_Api_Invoke32 direct win32k dispatch must use a current-thread Win32 state guard, not a process-level Win32 state guard
the source change keeps Thread_SetThreadToken, handler dispatch, Sbie_InvokeSyscall_asm, trap-frame restoration, and STATUS_INVALID_ADDRESS failure behavior intact
this SREV does not implement private GUI-thread conversion and does not change syscall table discovery
```

## Topology

Public GUI ownership shape:

```text
calling thread
  -> GUI-thread state
  -> desktop connection
  -> win32k syscall legality
```

Sandboxie source topology after this SREV:

```text
Syscall_Api_Invoke32
  -> Thread_SetThreadToken if policy allows
  -> ProbeForRead user args
  -> handler1_func path if present and allowed
  -> else require PsGetThreadWin32Thread(PsGetCurrentThread())
  -> Syscall_Invoke32
  -> Sbie_InvokeSyscall_asm
  -> restore trap-frame state
  -> Thread_ClearThreadToken
```

The old process-level guard was weaker topology:

```text
process has Win32Process state
  -/-> current thread has Win32Thread state
```

## Logic Risk

The stale todo named the right phenomenon but the wrong implementation boundary.
`PsConvertToGuiThread` and `KiConvertToGuiThread` are private kernel internals,
not documented driver DDIs. Calling them directly would tie Sandboxie to private
kernel layout and version behavior.

The actual local bug risk is narrower: direct `Sbie_InvokeSyscall_asm` bypasses
the normal kernel system-service entry path that would perform first-win32k-call
GUI-thread conversion. Since Microsoft documents the public shape as
calling-thread GUI state and thread desktop connection, a process-level
`PsGetProcessWin32Process` guard is not enough evidence that the current thread
is safe for direct win32k dispatch.

## Fix

Source-level behavior fix:

```text
Syscall_Api_Invoke32 now requires PsGetThreadWin32Thread(PsGetCurrentThread())
before direct win32k dispatch.
```

Preserved behavior:

```text
Thread_SetThreadToken and Thread_ClearThreadToken remain in the same positions.
handler1_func dispatch is unchanged.
Sbie_InvokeSyscall_asm selection between ntos_func and ntos_func2 is unchanged.
Trap-frame save/restore is unchanged.
The failure status remains STATUS_INVALID_ADDRESS when the current thread is not a Win32 thread.
No private GUI-thread conversion call was added.
No syscall table discovery logic changed.
```

## Acceptance Gate

`docs/plan/check-srev-103.py` validates the draft-07 schema, official reference
URLs, the source guard change from process-level `PsGetProcessWin32Process` to
current-thread `PsGetThreadWin32Thread(PsGetCurrentThread())`, removal of the
stale private-call todo, preservation of dispatch/failure topology, and the
ledger entry. `docs/plan/check-srev-103.sh` is the matrix wrapper.

Runtime gate: Windows x64 and x86 matrix with a sandboxed non-GUI thread in a
Win32-initialized process, a sandboxed GUI thread, `OpenWinClass` / win32k hook
paths, `UseWin32kFilterTable` on/off, HVCI on/off, Driver Verifier, and
observation that non-GUI current threads return `STATUS_INVALID_ADDRESS` rather
than reaching direct win32k dispatch.
