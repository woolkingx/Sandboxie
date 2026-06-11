# SREV-117 Process Util Allocation Lifetime

## Data

Owner file:

```text
Sandboxie/core/drv/process_util.c
```

Reviewed nodes:

```text
Process_LogMessage
Process_ScheduleKill
Process_ScheduleKillProc
Mem_Alloc
Mem_Free
RtlStringCbPrintfW
PsCreateSystemThread
ZwClose
PsTerminateSystemThread
Driver_Pool
proc->pool
```

## Schema

`PROCESS_UTIL_ALLOCATION_LIFETIME` defines these local contracts:

- `Mem_Alloc` may return `NULL` because its pool backend may fail allocation.
- Any buffer passed to `RtlStringCbPrintfW` must be allocated before use.
- `Process_LogMessage` may skip logging when the transient log-text allocation
  fails.
- `Process_ScheduleKill` owns the two-slot thread context until
  `PsCreateSystemThread` succeeds.
- After `PsCreateSystemThread` succeeds, `Process_ScheduleKillProc` owns and
  frees the thread context.
- If `PsCreateSystemThread` fails, `Process_ScheduleKill` frees the thread
  context and returns `FALSE`.
- The returned system-thread handle remains closed by the caller after
  successful `PsCreateSystemThread`.
- This SREV does not change termination policy, delay/retry behavior, process
  handle access masks, service-cancel fallback, log message ids, or worker
  termination status.

## Topology

```text
Process_LogMessage
  -> Mem_Alloc(proc->pool)
  -> if NULL: skip transient log text
  -> RtlStringCbPrintfW
  -> Log_MsgP1
  -> Mem_Free

Process_ScheduleKill
  -> Mem_Alloc(Driver_Pool) for two-slot context
  -> PsCreateSystemThread(Process_ScheduleKillProc, params)
      success:
        caller closes returned thread handle with ZwClose
        worker owns params and frees it at entry
      failure:
        caller frees params
        caller returns FALSE
```

## Logic Risk

`Process_ScheduleKill` allocated a two-pointer context and immediately wrote
`params[0]` / `params[1]` without checking the allocation result. If pool
allocation failed, this was a kernel null dereference on a termination path.

The same function transferred the context to `Process_ScheduleKillProc` only if
`PsCreateSystemThread` succeeded. When thread creation failed after context
allocation, the caller returned `FALSE` without freeing the context.

`Process_LogMessage` had the same allocation-before-use gap: if transient log
text allocation failed, the function still called `RtlStringCbPrintfW` with a
NULL destination. Logging is not the owner of termination or access-control
truth, so failure to allocate log text should skip only the log message.

## Official Shape

- https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-exallocatepoolwithtag
- https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-pscreatesystemthread
- https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-zwclose
- https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntstrsafe/nf-ntstrsafe-rtlstringcbprintfw

## Fix

`Process_LogMessage` now returns without logging when the transient text buffer
cannot be allocated. `Process_ScheduleKill` now returns `FALSE` if the two-slot
thread context cannot be allocated, and frees that context if
`PsCreateSystemThread` fails after allocation. The successful thread-create path
is unchanged: the caller closes the returned thread handle, and
`Process_ScheduleKillProc` frees the context at worker entry.

No kill scheduling delay, process lookup, `ObOpenObjectByPointer` access mask,
`ZwTerminateProcess` status, service-cancel fallback, or log message id changed.

## Acceptance Gate

Source gate:

```bash
python3 docs/plan/check-srev-117.py
bash docs/plan/check-srev-117.sh
```

Runtime/build gate still required:

- Windows driver build for the process-util translation unit.
- Fault-injection or verifier-backed pool allocation failure for
  `Process_LogMessage` and `Process_ScheduleKill`.
- Fault-injection of `PsCreateSystemThread` failure after context allocation,
  proving no `Driver_Pool` context leak.
- Normal immediate and delayed kill paths still create a worker, close the
  returned thread handle in the caller, free the context in
  `Process_ScheduleKillProc`, and terminate or retry with the existing status.
