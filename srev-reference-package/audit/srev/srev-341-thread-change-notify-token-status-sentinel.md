# SREV-341: Thread Change Notify Token Status Sentinel

| Field | Content |
|---|---|
| Stage | schema -> topology -> verify |
| Input artifact | `Sandboxie/core/drv/thread_token.c`, `Sandboxie/core/drv/syscall.c`, `Sandboxie/core/dll/gui.c`, SREV-329, SREV-333, Microsoft `Nt/ZwSetInformationThread`, `PsReferenceImpersonationToken`, `PsImpersonateClient`, and privilege-constant documentation |
| Output artifact | Source comment owner, draft-07 schema, checker, and ledger fragment |
| Owner | `Thread_SetInformationThread_ChangeNotifyToken` / `Syscall_Api_Invoke` local status sentinel |
| Acceptance gate | Targeted checker validates official references, current-thread `ThreadImpersonationToken` trigger, change-notify token construction, `STATUS_THREAD_NOT_IN_PROCESS` sentinel producer/consumer, stale hack wording removal, SREV-329/SREV-333 adjacency, and ledger fragment |

## Data

`Thread_SetInformationThread_ImpersonationToken` intercepts
`NtSetInformationThread(ThreadImpersonationToken)` for sandboxed processes with a
primary token. It validates that `InfoBuffer` is a `HANDLE`, reads the requested
token handle, and recognizes a Sandboxie-private current-thread signal:

```text
ThreadHandle == NtCurrentThread()
MyTokenHandle == NtCurrentThread()
```

On that private signal it calls `Thread_SetInformationThread_ChangeNotifyToken`.
That helper selects the current thread impersonation token when present, or the
process primary token otherwise, then calls `Token_Restrict` with
`DISABLE_MAX_PRIVILEGE`. The local intent is to keep a restricted token that
still has the change-notify privilege needed for the early
`Gui_ConnectToWindowStationAndDesktop` path.

`Syscall_Api_Invoke` normally clears thread impersonation before returning to
user mode when `proc->primary_token` exists. The change-notify-token helper
therefore returns a local sentinel, `STATUS_THREAD_NOT_IN_PROCESS`, after
successful impersonation. `Syscall_Api_Invoke` consumes that sentinel only when
the syscall entry is `SetInformationThread` and the target thread argument is
`NtCurrentThread()`, converts the returned status to `STATUS_SUCCESS`, and skips
`Thread_ClearThreadToken`.

## Official Shape

Microsoft documents `NtSetInformationThread` / `ZwSetInformationThread` as a
thread-information transition taking a thread handle, information class,
information pointer, byte length, and returning an NTSTATUS value. The public
documentation does not define Sandboxie's private current-thread
`ThreadImpersonationToken` signal or the local sentinel.

Microsoft documents `PsReferenceImpersonationToken` as returning a referenced
impersonation token for a thread and returning `NULL` when the thread is not
currently impersonating. A non-NULL returned token must later be dereferenced.

Microsoft documents `PsImpersonateClient` as assigning an impersonation token to
a thread; passing `NULL` ends impersonation. It also warns that raising an
untrusted user thread's privilege state is extremely unsafe.

Microsoft documents `SE_CHANGE_NOTIFY_NAME` as the "Bypass traverse checking"
privilege.

Official references:

- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/nf-ntifs-ntsetinformationthread`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntddk/nf-ntddk-zwsetinformationthread`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/nf-ntifs-psreferenceimpersonationtoken`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/nf-ntifs-psimpersonateclient`
- `https://learn.microsoft.com/en-us/windows/win32/secauthz/privilege-constants`

## Boundary

```text
Gui_ConnectToWindowStationAndDesktop
  -> NtSetInformationThread(CurrentThread, ThreadImpersonationToken, CurrentThread)
  -> Thread_SetInformationThread
  -> Thread_SetInformationThread_ImpersonationToken
  -> Thread_SetInformationThread_ChangeNotifyToken
  -> Thread_MyImpersonateClient
  -> STATUS_THREAD_NOT_IN_PROCESS sentinel
  -> Syscall_Api_Invoke current-thread SetInformationThread consumer
  -> STATUS_SUCCESS without Thread_ClearThreadToken
```

`Thread_SetInformationThread_ChangeNotifyToken` owns producing the local
sentinel. `Syscall_Api_Invoke` owns consuming it at the syscall-return boundary.
Neither owner changes the documented `NtSetInformationThread` ABI; this is a
Sandboxie-private signal carried through an NTSTATUS slot.

## Topology

```text
Thread_SetInformationThread_ImpersonationToken
  -> InfoLength == sizeof(HANDLE)
  -> ProbeForRead(InfoBuffer)
  -> MyTokenHandle
  -> ThreadHandle == NtCurrentThread()
  -> MyTokenHandle == NtCurrentThread()
  -> Thread_SetInformationThread_ChangeNotifyToken

Thread_SetInformationThread_ChangeNotifyToken
  -> one-shot proc->change_notify_token_flag
  -> PsReferenceImpersonationToken(PsGetCurrentThread())
  -> fallback proc->primary_token reference
  -> Token_Restrict(... DISABLE_MAX_PRIVILEGE ...)
  -> Thread_MyImpersonateClient(... SecurityImpersonation)
  -> proc->change_notify_token_flag = TRUE
  -> STATUS_THREAD_NOT_IN_PROCESS

Syscall_Api_Invoke
  -> status == STATUS_THREAD_NOT_IN_PROCESS
  -> entry == Syscall_SetInformationThread
  -> user_args[0] == NtCurrentThread()
  -> status = STATUS_SUCCESS
  -> skip Thread_ClearThreadToken
```

## Logic Risk

The old wording called this a hack with a special status code. That hid the
actual contract: a local NTSTATUS sentinel crosses from the thread-token owner
to the syscall-return owner so one early GUI setup call can return with a
restricted impersonation token still active. Future edits that broaden the
consumer, clear the token unconditionally, or reuse `STATUS_THREAD_NOT_IN_PROCESS`
for another path could break the early non-zero-session window-station/desktop
setup or leave impersonation active for the wrong syscall.

## Fix

Comment-only source clarification. `thread_token.c` now names SREV-341 and
states that `STATUS_THREAD_NOT_IN_PROCESS` is a local current-thread
change-notify-token sentinel used to return with impersonation still active.
`syscall.c` now names the corresponding current-thread `SetInformationThread`
consumer. No token selection, filtering, impersonation call, sentinel value,
flag, status conversion, or token-clear behavior changed.

## Acceptance Gate

`docs/plan/check-srev-341.py` validates the draft-07 schema, official
references, `Thread_SetInformationThread_ImpersonationToken` trigger,
`Thread_SetInformationThread_ChangeNotifyToken` token selection/filtering,
`STATUS_THREAD_NOT_IN_PROCESS` producer, `Syscall_Api_Invoke` consumer, stale
hack wording removal, SREV-329 / SREV-333 adjacency, combined ledger entry, and
split ledger fragment.

Runtime gate: Windows VM matrix for non-zero-session process initialization and
`Gui_ConnectToWindowStationAndDesktop`, proving the current-thread
change-notify-token request returns success with impersonation intentionally
preserved, normal `NtSetInformationThread` paths still clear temporary
impersonation, repeated calls return the committed status, and browser/Kaspersky
adjacent paths from SREV-329/SREV-333 do not regress.
