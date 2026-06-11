# SREV-010 UAC Helper Wait Boundary

Status: source-level spec before patch.

## Official Shape

Microsoft documents `WaitForSingleObject` as waiting until the object is
signaled or the timeout elapses. If `dwMilliseconds` is `INFINITE`, the function
returns only when the object becomes signaled. It can return `WAIT_OBJECT_0`,
`WAIT_TIMEOUT`, or `WAIT_FAILED`.

Microsoft documents process termination as signaling the process object and
changing the process exit status. It also warns not to terminate arbitrary
processes unless their threads are in known states because `TerminateProcess`
does not run normal cleanup.

Sources:

- https://learn.microsoft.com/en-us/windows/win32/api/synchapi/nf-synchapi-waitforsingleobject
- https://learn.microsoft.com/en-us/windows/win32/procthread/terminating-a-process
- https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/ns-processthreadsapi-process_information

## Local Shape

When `UseSandboxieUAC` is enabled, SbieSvc launches Sandboxie's own
`Start.exe uac_prompt ...` helper in the target session and waits for it to exit
with `IDYES` or `IDNO`.

The helper process is not an arbitrary child process. It is a dedicated
Sandboxie prompt process launched only for this broker decision.

If this pre-prompt path fails, the existing code already calls
`RunUacSlave3(..., JustFail=true, ...)`, which writes the failure/cancel result
back to the caller.

## Local Risk

The previous `WaitForSingleObject(pi.hProcess, INFINITE)` can pin the service
worker forever if the prompt helper hangs, never shows, or cannot exit. That is
a broker-lifetime bug: a UI helper lifetime crosses into SbieSvc worker
availability without a bound.

## Patch Boundary

Only bound the dedicated Sandboxie `uac_prompt` helper wait. Do not change the
later UAC execution path and do not change policy decisions for normal prompt
answers.

The prompt helper now has a five-minute service-side timeout:

- `WAIT_OBJECT_0`: read the helper exit code as before.
- `WAIT_TIMEOUT`: terminate the dedicated helper, set `ERROR_TIMEOUT`, and fail
  closed through the existing `JustFail` path.
- `WAIT_FAILED`: fail closed through the existing `JustFail` path.

## Acceptance Gate

- The `uac_prompt` helper wait is no longer `INFINITE`.
- Timeout uses a named constant, not an inline magic number.
- Timeout/failure sets `ok = FALSE`, preserving the existing fail-closed
  `RunUacSlave3(..., JustFail=true, ...)` path.
- Runtime gate remains open: hung `Start.exe uac_prompt` does not pin an SbieSvc
  worker forever; normal `IDYES` and `IDNO` prompt exits keep current behavior.
