# SREV-044: Token Handle Writeback

## Finding

`Sandboxie/core/drv/thread_token.c` opens token handles for
`Thread_OpenProcessToken_Common` and `Thread_OpenThreadToken_Common`, then
writes the resulting `HANDLE` through a user `HANDLE*` output pointer. The old
finish path wrote `*TokenHandle = MyTokenHandle` inside `try/except`; if that
write failed after the token handle had been opened, the function returned the
exception status while leaving the opened handle unclosed.

The same paths also probed the output pointer with byte alignment even though
the boundary shape is a `HANDLE*`.

## Official Shape

- `ProbeForWrite` takes a byte length and required start-address alignment, and
  callers must still handle exceptions around later accesses:
  `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-probeforwrite`
- `ZwClose` closes an object handle, and drivers must close handles they open
  when no longer required:
  `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-zwclose`

## Local Schema

Machine-readable schema:

```text
docs/plan/srev-044-token-handle-writeback.schema.json
```

`TokenHandle` is a user-mode `HANDLE*` output pointer. `MyTokenHandle` remains
driver-owned until the writeback succeeds. A failed writeback must close and
clear `MyTokenHandle` because ownership was never transferred to the caller.

## Fix

`Thread_WriteTokenHandleToUser` now owns the token-handle output boundary for
both process-token and thread-token open paths. It probes the output pointer as
a `HANDLE*`, writes the opened handle inside `try/except`, and closes/clears the
opened handle if writeback fails.

## Acceptance Gate

`docs/plan/check-srev-044.py` validates the schema, official references, helper
shape, `sizeof(HANDLE)` alignment, removal of the old direct writeback blocks,
and routing from both token-open common helpers.

Windows gate still needed: force an invalid or racing `TokenHandle` output
pointer after a token handle can be opened and verify the call fails without
leaking the opened token handle; normal `NtOpenProcessToken*` and
`NtOpenThreadToken*` paths still return usable caller handles.
