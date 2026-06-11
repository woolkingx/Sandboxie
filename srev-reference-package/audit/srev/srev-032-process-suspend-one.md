# SREV-032: SuspendOne Process Handle Shape

## Finding

`Sandboxie/core/svc/ProcessServer.cpp` opened a target process for
`PROCESS_SUSPEND_RESUME`, then passed the returned handle directly to
`NtSuspendProcess` or `NtResumeProcess` and finally called `CloseHandle`.

The sibling `SuspendAllHandler` already gates the same operation with
`if (hProcess)` before calling the native suspend/resume routine and closing the
handle. `SuspendOneHandler` had the same handle-owner boundary but lacked the
gate.

## Official API Shape

Primary Microsoft references:

- `https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-openprocess`
- `https://learn.microsoft.com/en-us/windows/win32/api/handleapi/nf-handleapi-closehandle`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/kernel/using-ntstatus-values`

Relevant contract:

- `OpenProcess` returns an open process handle on success.
- `OpenProcess` returns `NULL` on failure; extended error information is in
  `GetLastError`.
- `CloseHandle` takes a valid handle to an open object.
- Local SbieSvc replies carry status values through `SHORT_REPLY`.

## Local Schema

Small machine-readable schema:

```text
docs/plan/srev-032-process-suspend-one.schema.json
```

Request:

```text
MSG_HEADER
pid
suspend
```

The request selects exactly one target process. Process identity, box/session
authorization, and caller authorization must pass before the service opens the
target process with `PROCESS_SUSPEND_RESUME`.

## Source Change

`SuspendOneHandler` now checks the `OpenProcess` result before native
suspend/resume:

- `NULL` process handle returns `STATUS_INVALID_CID`;
- `NtSuspendProcess` / `NtResumeProcess` only receive a valid opened handle;
- `CloseHandle` only runs on the success path after native suspend/resume.

## Acceptance Gate

Source-level gate:

- `docs/plan/check-srev-032.py` validates the local schema and source handle
  order.
- No direct `NtSuspendProcess(hProcess)` / `NtResumeProcess(hProcess)` path may
  occur before the `if (! hProcess)` guard in `SuspendOneHandler`.

Windows runtime gate:

- Suspend/resume a valid sandboxed process from an authorized unsandboxed
  caller.
- Race or deny the target open so `OpenProcess` returns `NULL`, then confirm the
  service returns `STATUS_INVALID_CID` without using or closing the invalid
  handle.
