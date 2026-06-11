# SREV-121 User Server Duplicate Handle Result Gate

## Data

Owner file:

```text
Sandboxie/core/svc/UserServer.cpp
```

Reviewed nodes:

```text
UserServer::StartWorker
UserServer::OpenFile
DuplicateHandle
QueueUserAPC
OpenProcess
CloseHandle
USER_OPEN_FILE_RPL.FileHandle
STATUS_UNSUCCESSFUL
```

## Schema

`USER_SERVER_DUPLICATE_HANDLE_RESULT_GATE` defines these local contracts:

- `DuplicateHandle` returns a Win32 `BOOL`, not an `NTSTATUS`.
- `DuplicateHandle` success is nonzero and failure is zero; callers must not use
  `NT_SUCCESS(DuplicateHandle(...))`.
- `StartWorker` only queues the duplicated service-process handle to the worker
  thread after `DuplicateHandle` succeeds.
- If `QueueUserAPC` fails after a successful duplicate, `StartWorker` closes the
  locally owned duplicate handle instead of leaking it.
- `OpenFile` initializes the reply file handle to zero before attempting to
  duplicate the broker-opened file handle into the caller.
- `OpenFile` reports a failed file-handle duplication through `rpl->error`
  instead of returning an uninitialized or stale reply handle as if the open
  fully succeeded.
- This SREV does not change user-worker token selection, event security,
  file-policy path matching, requested access, `NtCreateFile` arguments, or
  queue request routing.

## Topology

```text
StartWorker
  -> DuplicateHandle(current service process pseudo handle -> worker process)
      -> QueueUserAPC(worker thread, duplicated handle)
      -> CloseHandle(duplicate) if APC enqueue fails

OpenFile
  -> NtCreateFile in broker
      -> OpenProcess(PROCESS_DUP_HANDLE, caller pid)
      -> DuplicateHandle(broker file handle -> caller process)
      -> USER_OPEN_FILE_RPL.FileHandle or STATUS_UNSUCCESSFUL
      -> NtClose(broker file handle)
```

## Logic Risk

The old `StartWorker` path wrapped `DuplicateHandle` with `NT_SUCCESS`. That is
wrong for a Win32 `BOOL` API: `FALSE` is zero, and zero satisfies the
`NT_SUCCESS` macro check. A failed duplicate could therefore still queue an APC
with an uninitialized handle value.

The old `OpenFile` path also ignored the `DuplicateHandle` return value. If the
broker opened the file but failed to duplicate the handle into the caller, the
reply could still carry success in `rpl->error` and an uninitialized
`FileHandle`. The legal local repair is a result gate on the existing handle
crossing, not a change to file policy, token policy, or request routing.

## Official Shape

- https://learn.microsoft.com/en-us/windows/win32/api/handleapi/nf-handleapi-duplicatehandle
- https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-queueuserapc
- https://learn.microsoft.com/en-us/windows/win32/api/handleapi/nf-handleapi-closehandle
- https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-openprocess

## Fix

`StartWorker` now initializes `hThis` to `NULL`, gates `QueueUserAPC` on
nonzero `DuplicateHandle` success, and closes `hThis` if `QueueUserAPC` fails
after the duplicate was created.

`OpenFile` now initializes `rpl->FileHandle` to zero before the broker
`NtCreateFile` call and sets `rpl->error = STATUS_UNSUCCESSFUL` if the
broker-opened file handle cannot be duplicated into the caller process.

No user-worker token selection, event security descriptor, process creation
flags, file-policy matching, requested file access, EA-buffer handling,
`NtCreateFile` argument shape, broker-side `NtClose`, or queue callback routing
changed.

## Acceptance Gate

Source gate:

```bash
python3 docs/plan/check-srev-121.py
bash docs/plan/check-srev-121.sh
```

Runtime/build gate still required:

- Windows service build for `UserServer.cpp`.
- Worker startup smoke where `DuplicateHandle` succeeds and the worker receives
  the parent-process synchronization handle through APC.
- Fault-injection or debugger-assisted smoke where worker APC enqueue fails and
  the duplicated handle is closed.
- Sandboxed `USER_OPEN_FILE` positive smoke proving duplicated file handles are
  usable by the caller.
- Negative smoke where `OpenProcess(PROCESS_DUP_HANDLE)` or `DuplicateHandle`
  fails and the reply carries `STATUS_UNSUCCESSFUL` with zero `FileHandle`.
