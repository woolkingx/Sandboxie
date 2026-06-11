# SREV-021: UAC Slave Thread Handle Ownership

## Stage Gate

| Field | Content |
|---|---|
| Stage | schema -> topology -> logic -> action |
| Input Artifact | `Sandboxie/core/svc/serviceserver2.cpp` UAC slave thread creation |
| Output Artifact | Source-level handle ownership fix plus `docs/plan/check-srev-021.sh` |
| Owner | `ServiceServer::RunUacSlave2` |
| Acceptance Gate | Thread handles returned by `CreateThread` are closed when the caller does not need to wait, signal, or query them. |

## Official Shape

Microsoft `CreateThread` documentation defines a successful return value as a
handle to the new thread:

```text
https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-createthread
```

Microsoft `CloseHandle` documentation lists `Thread` as a closeable object type
and states that closing a thread handle does not terminate the associated
thread:

```text
https://learn.microsoft.com/en-us/windows/win32/api/handleapi/nf-handleapi-closehandle
```

Microsoft's thread-creation example stores the returned thread handles, waits
for the workers in that example, then closes every thread handle:

```text
https://learn.microsoft.com/en-us/windows/win32/procthread/creating-threads
```

The API contract is therefore handle ownership, not worker lifetime ownership:
if the creator no longer needs the returned handle, it should close the handle.
Closing the handle must not be used as a worker cancellation mechanism.

## Local Shape

`RunUacSlave2` starts two helper threads in two branches:

1. the already-admin fast path;
2. the dialog-confirmed path after the user approves UAC handling.

Both workers are fire-and-forget in the current topology:

- `RunUacSlave2Thread1` runs the elevated `ShellExecuteExW(..., runas, ...)`
  path or fails the UAC packet closed, then exits the helper process.
- `RunUacSlave2Thread2` watches the caller process and exits the helper process
  when the caller exits.

No later local code waits on, signals, duplicates, or queries the returned
thread handles.

## Finding

The source comments said the code was "leaking a thread" beside each
`CreateThread` call. The local evidence shows the concrete leak is the returned
thread handle: the worker lifetime is intentionally controlled by the helper
process, but the creator kept no owned handle variable and never closed it.

## Patch Boundary

The patch only closes non-NULL handles returned by `CreateThread` in both local
branches. It does not change:

- UAC prompt flow;
- helper thread entry points;
- process lifetime;
- the existing suspended caller thread behavior.

## Runtime Gate

Windows runtime proof still requires UAC prompt coverage:

1. already-admin auto-approve path creates both workers without handle growth;
2. dialog-confirmed path creates both workers without handle growth;
3. elevation cancellation still routes through the existing fail-closed path;
4. caller-process exit still terminates the helper process.
