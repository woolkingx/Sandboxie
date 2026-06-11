# SREV-203: GUI Window Hook Register Lock Exit

## Stage

schema -> boundary -> topology -> logic -> action -> verify

## Evidence

`Sandboxie/core/svc/GuiServer.h` was the top unnamed reviewable core file after
SREV-202. Its implementation in `Sandboxie/core/svc/GuiServer.cpp` owns the GUI
proxy request handlers, including the `GUI_WND_HOOK_REGISTER` path that
registers a caller-owned hook helper thread in `m_WndHooks`.

Before this fix, `GuiServer::WndHookRegisterSlave` entered `m_SlavesLock` and
then returned directly if `OpenThread(THREAD_QUERY_LIMITED_INFORMATION, ...)`
failed or if `GetProcessIdOfThread` showed that the supplied thread did not
belong to the requesting process. Those exits skipped `LeaveCriticalSection`.
The same registration path allocated a new `WND_HOOK` entry without checking
for allocation failure.

## Data

`GUI_WND_HOOK_REGISTER_REQ`, `GUI_WND_HOOK_REGISTER_RPL`, `m_SlavesLock`,
`m_WndHooks`, `WND_HOOK`, `req->hthread`, `req->hproc`, `args->pid`,
`OpenThread`, `GetProcessIdOfThread`, `CloseHandle`, `HeapAlloc`,
`List_Insert_After`, and `LeaveCriticalSection`.

## Official Shape

Microsoft documents `EnterCriticalSection` as acquiring ownership of a
critical section and `LeaveCriticalSection` as releasing that ownership. The
same documentation says a thread must call `LeaveCriticalSection` once for each
successful entry, and that failure to release ownership can make other threads
wait indefinitely.

Microsoft documents `OpenThread` as returning an open thread handle on success
and `NULL` on failure. It also states the returned handle should be closed with
`CloseHandle` when no longer needed. `GetProcessIdOfThread` requires a thread
handle with query access and returns zero on failure. `HeapAlloc` returns
`NULL` on failure when exceptions are not requested.

References:

- `https://learn.microsoft.com/en-us/windows/win32/api/synchapi/nf-synchapi-entercriticalsection`
- `https://learn.microsoft.com/en-us/windows/win32/api/synchapi/nf-synchapi-leavecriticalsection`
- `https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-openthread`
- `https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-getprocessidofthread`
- `https://learn.microsoft.com/en-us/windows/win32/api/handleapi/nf-handleapi-closehandle`
- `https://learn.microsoft.com/en-us/windows/win32/api/heapapi/nf-heapapi-heapalloc`

## Schema

`GUI_WND_HOOK_REGISTER_LOCK_EXIT` says:

- The `m_WndHooks` list is accessed only while `m_SlavesLock` is held.
- Every exit after `EnterCriticalSection(&m_SlavesLock)` must pass through a
  single `LeaveCriticalSection(&m_SlavesLock)` edge.
- Thread ownership validation failures preserve the existing outer NTSTATUS
  failure result, but only after releasing the lock.
- A successful `OpenThread` handle is closed before any owner mismatch decision
  returns to the caller.
- A new `WND_HOOK` list entry is inserted only after `HeapAlloc` succeeds.
- The successful register/unregister request topology and reply shape are
  preserved.

## Topology

```text
GUI_WND_HOOK_REGISTER request
-> fixed-size wire gate
-> EnterCriticalSection(m_SlavesLock)
-> find existing WND_HOOK by caller pid
-> register path:
   OpenThread(req->hthread)
   -> GetProcessIdOfThread
   -> CloseHandle(hThread)
   -> owner-pid gate
   -> HeapAlloc WND_HOOK if needed
   -> List_Insert_After / HookCount++
-> unregister path:
   HookCount-- / remove last entry
-> LeaveCriticalSection(m_SlavesLock)
-> success reply or preserved outer failure status
```

## Logic Risk

The old direct returns could leave the GUI slave critical section owned after a
malformed or stale hook-register request. Later GUI proxy requests using the
same lock could then hang behind the leaked lock even though the process stayed
alive. The unchecked allocation could also crash while the lock was held.

## Fix

`WndHookRegisterSlave` now stores the failure status, routes all post-lock
failure exits through a `finish` label, calls `LeaveCriticalSection` before
returning the preserved failure status, checks `HeapAlloc` before writing a
new `WND_HOOK`, and keeps the successful reply behavior unchanged.

## Acceptance Gate

`docs/plan/check-srev-203.py` validates the draft-07 schema, official
references, header/implementation owner coordinates, the post-lock single-exit
shape, stale direct returns removal from the locked region, `CloseHandle` before
owner mismatch failure, allocation failure handling, and split ledger fragment.
Runtime/build gate: Windows service build plus malformed/stale
`GUI_WND_HOOK_REGISTER` request smoke proving subsequent GUI proxy requests do
not hang behind `m_SlavesLock`.
