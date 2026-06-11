# SREV-159: PipeServer Thread Vector Lifetime

## Stage Gate

```text
stage: schema -> boundary -> topology -> logic -> action -> verify
input artifact: Sandboxie/core/svc/PipeServer.h and Sandboxie/core/svc/PipeServer.cpp
output artifact: counted worker-thread handle vector with startup-failure cleanup
owner: Sandboxie/core/svc/PipeServer.cpp
acceptance gate: docs/plan/check-srev-159.py and docs/plan/check-srev-159.sh
```

## Data

`PipeServer` owns the SbieSvc LPC server port and its worker thread handles.
`PipeServer.h` declares the server lifecycle state: `m_hServerPort`,
`m_Threads`, and now `m_ThreadCount`. `PipeServer.cpp` allocates the thread
handle vector in the constructor, creates worker threads in `Start`, and tears
down the server in the destructor.

Before this SREV, the constructor logged `HeapAlloc` failure but `Start`
unconditionally indexed `m_Threads[i]` after creating the server port. A
partial `CreateThread` failure returned `false` while leaving the port and any
already-created worker threads live. The destructor waited on
`NUMBER_OF_THREADS` handles whenever `m_Threads` was non-null, even if `Start`
never created that many thread handles, and it did not close thread handles or
free the `HeapAlloc` thread-vector storage.

## Official Shape

- Microsoft documents `HeapAlloc` as returning `NULL` on failure when
  `HEAP_GENERATE_EXCEPTIONS` is not specified:
  `https://learn.microsoft.com/en-us/windows/win32/api/heapapi/nf-heapapi-heapalloc`.
- Microsoft documents `CreateThread` as returning a handle on success and
  `NULL` on failure, with extended error from `GetLastError`; it also states
  the thread object remains until the thread terminates and all handles are
  closed:
  `https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-createthread`.
- Microsoft documents `WaitForMultipleObjects` as taking the number of handles
  and an array of handles, with the count not zero:
  `https://learn.microsoft.com/en-us/windows/win32/api/synchapi/nf-synchapi-waitformultipleobjects`.
- Microsoft documents `CloseHandle` as closing valid object handles including
  thread handles:
  `https://learn.microsoft.com/en-us/windows/win32/api/handleapi/nf-handleapi-closehandle`.
- Microsoft documents `HeapFree` as freeing memory allocated by `HeapAlloc`:
  `https://learn.microsoft.com/en-us/windows/win32/api/heapapi/nf-heapapi-heapfree`.

## Schema

`PIPESERVER_THREAD_VECTOR_LIFETIME` says:

- `PipeServer` owns a thread handle vector allocated from `GetProcessHeap`.
- `Start` must not create the server port or index `m_Threads` when the vector
  allocation failed.
- `m_ThreadCount` is the number of valid thread handles currently stored at the
  front of `m_Threads`.
- waits, termination, close, and cleanup may operate only on `m_ThreadCount`
  valid handles, not on the full vector capacity when startup was partial.
- every successful `CreateThread` handle is eventually closed with
  `CloseHandle`.
- startup failure after partial thread creation shuts down the published port,
  wakes existing worker threads, closes their handles, preserves the
  `GetLastError` value from `CreateThread`, and returns `false`.
- the `HeapAlloc` vector is freed with `HeapFree` in the destructor.
- this SREV does not change LPC message framing, request dispatch, target
  registration, impersonation, or server-port security descriptor policy.

## Topology

Legal startup flow:

```text
constructor -> HeapAlloc thread vector -> Start
Start -> m_Threads allocation gate
      -> security descriptor and NtCreatePort
      -> CreateThread loop
      -> m_Threads[0..m_ThreadCount) are valid thread handles
      -> success only after all NUMBER_OF_THREADS handles exist
```

Legal failure/shutdown flow:

```text
partial startup failure or destructor
-> exchange m_hServerPort to NULL
-> wake worker threads through old port handle
-> WaitForMultipleObjects(m_ThreadCount, m_Threads, ...)
-> terminate only counted handles on timeout
-> CloseHandle each counted thread handle
-> NtClose old port handle
-> destructor HeapFree(m_Threads)
```

## Logic Risk

The worker-thread vector is capacity storage, not proof that handles exist.
Treating an allocated vector as a fully populated handle array can send
`WaitForMultipleObjects` invalid handles or dereference a null vector in
`Start`. Treating a partial `CreateThread` failure as a plain startup failure
without cleanup can leave a reachable SbieSvc port and worker threads alive
after `InitializePipe` reports service startup failure. The correct local owner
repair is to count valid handles and make port/thread teardown reusable by both
destructor and startup-failure paths.

## Fix

`PipeServer` now tracks `m_ThreadCount`, checks `m_Threads` before creating the
server port, and increments the count only after each `CreateThread` succeeds.
`ShutdownPortAndThreads` owns the common teardown path: it withdraws
`m_hServerPort`, wakes workers, waits only on counted handles, terminates only
counted handles on timeout, closes each counted thread handle, resets the
count, and closes the old port handle. `Start` calls this cleanup on partial
thread startup failure while preserving the `CreateThread` error. The destructor
calls the same cleanup and frees the `HeapAlloc` thread vector with `HeapFree`.

## Verification

Source-level gates:

```bash
python3 docs/plan/check-srev-159.py
bash docs/plan/check-srev-159.sh
python3 docs/plan/check-core-coverage.py
```

Full closure matrix:

```bash
python3 docs/plan/check-srev-159.py &&
bash docs/plan/check-srev-159.sh &&
python3 docs/plan/check-core-coverage.py &&
for s in docs/plan/check-srev-0*.sh docs/plan/check-srev-1*.sh docs/plan/check-kpath-0*.sh; do bash "$s"; done &&
git diff --check
```

Runtime/build gate: Windows SbieSvc build; forced `HeapAlloc` failure proving
`Start` returns `ERROR_NOT_ENOUGH_MEMORY` before publishing the port; forced
mid-loop `CreateThread` failure proving already-created workers exit and handles
are closed; ordinary startup/shutdown smoke proving all worker handles close and
normal LPC requests still dispatch.
