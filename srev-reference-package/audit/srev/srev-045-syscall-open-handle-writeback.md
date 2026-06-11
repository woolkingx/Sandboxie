# SREV-045: Syscall Open Handle Writeback

## Finding

`Sandboxie/core/drv/syscall_open.c` redirects syscall output handles into a
temporary user TLS slot, restores the original output pointer, validates the
opened object, then writes `NewHandle` back to the original user `HANDLE*`.

The pre-patch finish blocks in `Syscall_OpenHandle`, `Syscall_GetNextProcess`,
and `Syscall_DuplicateHandle` wrote `*UserHandlePtr = NewHandle` inside
`try/except`. If that writeback raised after `NewHandle` had been opened and
accepted, the function returned `STATUS_PROCESS_IS_TERMINATING` without closing
the still driver-owned handle. `Syscall_ReplaceTargetHandle` also probed
`UserHandlePtr` with byte alignment even though the boundary shape is a
`HANDLE*`.

## Official Shape

- `ProbeForWrite` takes a byte length and required start-address alignment, and
  later user-buffer accesses still need exception handling:
  `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-probeforwrite`
- `NtClose` closes an object handle, and drivers must close handles they open
  as soon as the handle is no longer required:
  `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/nf-ntifs-ntclose`

## Local Schema

Machine-readable schema:

```text
docs/plan/srev-045-syscall-open-handle-writeback.schema.json
```

`UserHandlePtr` is the original user-mode `HANDLE*` output pointer. `NewHandle`
comes from the temporary TLS slot and remains driver-owned until writeback
succeeds. A writeback failure means ownership never reached the caller, so the
handle must be closed on the failure path.

## Fix

`Syscall_WriteRestoredHandleToUser` now owns the restored-handle output
boundary for `Syscall_OpenHandle`, `Syscall_GetNextProcess`, and
`Syscall_DuplicateHandle`. It probes the output pointer as a `HANDLE*`, writes
inside `try/except`, returns the original syscall status on success, and closes
`NewHandle` with `NtClose` if writeback fails.

## Acceptance Gate

`docs/plan/check-srev-045.py` validates the schema, official references, helper
shape, `sizeof(HANDLE)` alignment, removal of old direct writeback blocks, and
helper routing from all three syscall-open paths.

Windows gate still needed: race or invalidate the original output pointer after
the syscall writes the temporary TLS slot and verify accepted handles do not
leak; normal open/get-next/duplicate paths still return usable handles and
preserve non-zero success statuses.
