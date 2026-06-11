# SREV-198: SCM Notify APC Contract

Stage: schema -> boundary -> action -> verify

Input artifact: `Sandboxie/core/dll/scm_notify.c`

Output artifact: the Sandboxie SCM notification hook validates the caller's
`SERVICE_NOTIFY` buffer before dereference, starts its local watcher resources
only through checked handles, preserves the caller-buffer/APC topology, and does
not read service status data after freeing the broker reply.

Owner: `Sandboxie/core/dll/scm_notify.c`

Acceptance gate: `docs/plan/check-srev-198.py` plus
`docs/plan/check-srev-198.sh`.

## Data

`scm_notify.c` implements Sandboxie's local replacement for
`NotifyServiceStatusChangeA/W` and the related synchronous
`Scm_WaitServiceState` helper.

Important data crossings:

- `NotifyServiceStatusChangeW` receives an `SC_HANDLE`, a notification mask,
  and a caller-owned `SERVICE_NOTIFY` buffer.
- The hook opens the calling thread with `THREAD_SET_CONTEXT` so a later worker
  can queue an APC back to that thread.
- The worker polls Sandboxie's service-status broker, writes the resulting
  `SERVICE_STATUS_PROCESS` into the caller's `SERVICE_NOTIFY` buffer, then
  queues an APC that invokes the caller callback.
- `Scm_WaitServiceState` receives a broker reply, copies the current service
  state decision, frees the reply, and returns the copied state.

Local evidence before this entry:

- `Scm_NotifyServiceStatusChangeW` read `pNotifyBuffer->dwVersion` before
  proving that `pNotifyBuffer` was non-null.
- The hook did not validate the callback pointer before later calling through
  `pfnNotifyCallback`.
- Global watcher allocation, notification element allocation, event creation,
  and thread creation were not all checked before returning success.
- A re-registration for an existing service handle set `active = TRUE` but did
  not update the stored caller buffer or notification mask.
- `QueueUserAPC` was not checked, so a failed APC enqueue could silently clear
  the active notification and lose the callback.
- `Scm_WaitServiceState` returned `ss->dwCurrentState` after freeing the reply
  buffer that owned `ss`.

## Official API Shape

`NotifyServiceStatusChangeW` takes a caller-supplied `SERVICE_NOTIFY` pointer.
The buffer must remain valid until the callback is invoked or the request is
canceled, and the callback is delivered as an APC queued to the calling thread:

https://learn.microsoft.com/en-us/windows/win32/api/winsvc/nf-winsvc-notifyservicestatuschangew

`SERVICE_NOTIFY_2W` documents the structure shape: `dwVersion`, callback,
context, notification status, service status, trigger mask, and service names.
It also states that the callback receives a pointer to the caller-provided
structure:

https://learn.microsoft.com/en-us/windows/win32/api/winsvc/ns-winsvc-service_notify_2w

`OpenThread` returns `NULL` on failure and the returned thread handle must be
closed when it is no longer needed:

https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-openthread

`QueueUserAPC` requires a thread handle with `THREAD_SET_CONTEXT`; success is
nonzero and failure is zero with extended error from `GetLastError`:

https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-queueuserapc

`CreateEventW` and `CreateThread` both return `NULL` on failure and provide
extended error through `GetLastError`:

https://learn.microsoft.com/en-us/windows/win32/api/synchapi/nf-synchapi-createeventw

https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-createthread

`WaitForMultipleObjects` returns `WAIT_FAILED` on failure and
`WAIT_TIMEOUT` when its timeout elapses:

https://learn.microsoft.com/en-us/windows/win32/api/synchapi/nf-synchapi-waitformultipleobjects

`GetTickCount` returns a `DWORD` millisecond count and wraps after about
49.7 days, so elapsed-time comparisons must use copied values rather than stale
freed pointers:

https://learn.microsoft.com/en-us/windows/win32/api/sysinfoapi/nf-sysinfoapi-gettickcount

## Boundary

The boundary is:

```text
caller thread + SERVICE_NOTIFY buffer
  -> Sandboxie SCM notification hook
  -> Sandboxie service-status broker poll
  -> QueueUserAPC(caller thread, caller buffer)
  -> caller callback
```

`scm_notify.c` owns the local hook state and watcher handles. The caller owns
the `SERVICE_NOTIFY` buffer under the Windows API lifetime contract. Sandboxie
may store that pointer only while the request is outstanding and must not call
through it unless the buffer and callback shape passed the registration gate.

## Topology

```text
Scm_NotifyServiceStatusChangeW
  -> validate pNotifyBuffer, dwVersion, pfnNotifyCallback, and mask
  -> resolve hService through Scm_GetHandleName
  -> open caller thread with THREAD_SET_CONTEXT
  -> allocate/update SCM_NOTIFY_ELEM
  -> create watcher event/thread with checked return values
  -> publish caller buffer and mask to the active element

Scm_Notify_ThreadProc2
  -> query service state
  -> copy SERVICE_STATUS_PROCESS into caller buffer
  -> queue APC while holding notify lock
  -> mark inactive only when QueueUserAPC succeeds

Scm_Notify_ApcProc
  -> re-check that the notification element still owns the same buffer
  -> call pfnNotifyCallback only when the callback pointer is non-null

Scm_WaitServiceState
  -> copy dwCurrentState out of the broker reply
  -> free reply
  -> return the copied state
```

## Logic

The hook is a compatibility projection of the Windows SCM notification API, not
the real SCM. This SREV keeps the existing polling/APC design and fixes the
local owner gates that can be proven from source:

- no caller buffer dereference before pointer validation;
- no callback through a null `pfnNotifyCallback`;
- no success return when allocation, event creation, or watcher-thread creation
  failed;
- no stale buffer/mask after re-registering an existing service handle;
- no silent lost callback when `QueueUserAPC` fails;
- no read through `SERVICE_STATUS_PROCESS *ss` after the reply buffer is freed.

This entry does not add full SCM-manager create/delete notifications and does
not replace the polling model with native SCM state subscription. Those are
compatibility/runtime design items outside this owner-local hardening patch.

## Verification

Linux source gates prove:

- the buffer, version, callback, and mask are checked before registration;
- `OpenThread`, `Dll_Alloc`, `CreateEvent`, and `CreateThread` failures return
  failure instead of `ERROR_SUCCESS`;
- existing notification entries update their caller buffer and mask;
- `QueueUserAPC` success gates `active = FALSE`;
- the APC callback is called only through a non-null callback pointer;
- `Scm_WaitServiceState` returns a copied `current_state`, not a field inside a
  freed reply.

Runtime gate:

- Windows DLL build.
- NotifyServiceStatusChange smoke: null/invalid pointer negative cases,
  callback-positive service-state transition, re-registration with a new
  buffer/mask, APC enqueue failure or target-thread-exit fault injection, and
  `Scm_WaitServiceState` timeout/cancel/success coverage.
