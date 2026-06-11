# SREV-046: Process Query Token Handle

## Finding

`Sandboxie/core/drv/process_api.c` `Process_Api_QueryInfo` exposes token-related
query classes:

- `ptok`: return a primary token handle.
- `itok`: return an impersonation token handle for a thread.
- `ttok`: return whether a thread has an impersonation token.

The pre-patch `ptok` and `itok` paths opened token handles and then wrote those
handles directly through the user `info_data` pointer. If the user writeback
raised after the handle was opened, the opened handle stayed unclosed because
ownership never reached the caller.

The `itok` / `ttok` path also performed user output writes while
`proc->threads_lock` was held at APC_LEVEL. An exception during that write could
skip the lock release and IRQL restore by jumping to the outer exception
handler.

## Official Shape

- `ProbeForWrite` takes a byte length and required start-address alignment, and
  later user-buffer accesses still need exception handling:
  `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-probeforwrite`
- `NtClose` closes an object handle, and drivers must close handles they open
  as soon as the handle is no longer required:
  `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/nf-ntifs-ntclose`

## Local Schema

Machine-readable JSON Schema draft-07 contract:

```text
docs/plan/srev-046-process-query-token-handle.schema.json
```

`info_data` is a user `ULONG64*` output pointer. A token handle opened for
`ptok` or `itok` remains driver-owned until writeback succeeds. A thread-token
query may only reference the token object or snapshot a boolean while
`proc->threads_lock` is held; handle creation and user output writeback happen
after the lock is released and IRQL is lowered.

## Fix

`Process_Api_WriteQueryUlong64ToUser` owns the `ULONG64*` user-output writeback.
`Process_Api_WriteQueryHandleToUser` extends it for token handles and closes the
opened handle with `NtClose` if writeback fails.

The `ptok` path now writes opened primary token handles through the handle
helper. The `itok` / `ttok` path now only snapshots `ttok` state or references
the impersonation token object under `proc->threads_lock`; it releases the lock
and lowers IRQL before opening token handles or writing user output.

## Acceptance Gate

`docs/plan/check-srev-046.py` validates the draft-07 schema, helper shape,
handle-close failure path, removal of direct token-handle writes, and that the
thread-token path does not open token handles or write user output while
`proc->threads_lock` is held.

Windows gate still needed: `ptok`, `itok`, and `ttok` queries with valid output,
invalid/racing output, missing impersonation token, and normal sandboxed caller
denial. Handle count should not grow on invalid output after a token handle was
opened.
