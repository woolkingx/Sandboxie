# SREV-100: Process Create Caller Snapshot

## Data

`Sandboxie/core/drv/process.c` owns process-create and process-delete tracking
for the driver. The comment-admitted risk near the parent sandbox inheritance
path was a process lifetime problem:

```text
new process N
  -> inherited parent process id can name process A
  -> creating/calling process can be process B
  -> sandbox inheritance sometimes needs A's PROCESS box state
  -> A can exit while create handling is still running
```

The local topology already protects the parent `PROCESS` pointer by keeping
`Process_ListLock` held while it clones `parent_proc->box`. The narrower gap was
that Vista+ create notifications still passed `PsGetCurrentProcessId()` as the
caller identity even though the official `PS_CREATE_NOTIFY_INFO` structure
already carries the creator process id in `CreatingThreadId.UniqueProcess`.

## Official Shape

Microsoft documents `PsSetCreateProcessNotifyRoutineEx` as registering a
callback for process create/exit events. For process creation, the routine runs
in the context of the thread that created the new process; for deletion, it runs
in the context of the last thread to exit from the process.

Microsoft documents `PCREATE_PROCESS_NOTIFY_ROUTINE_EX` as receiving
`CreateInfo`; if `CreateInfo` is `NULL`, the process is exiting. Microsoft
documents `PS_CREATE_NOTIFY_INFO.ParentProcessId` as the parent process id for
the new process and explicitly says it is not necessarily the same as the
process that created the new process. The creator id is
`CreatingThreadId->UniqueProcess`.

The legacy `PsSetCreateProcessNotifyRoutine` callback does not provide
`PS_CREATE_NOTIFY_INFO`; it receives only `ParentId`, `ProcessId`, and the
create/delete flag. Microsoft documents this legacy create callback as called
after the initial thread is created within the new process, and says `ParentId`
identifies the inherited parent.

Microsoft documents `ERESOURCE` as read/write locking for drivers and
`ExAcquireResourceExclusiveLite` as acquiring a resource for exclusive access;
the caller releases it with `ExReleaseResourceLite` or
`ExReleaseResourceForThreadLite`.

```text
https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntddk/nf-ntddk-pssetcreateprocessnotifyroutineex
https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntddk/nc-ntddk-pcreate_process_notify_routine_ex
https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntddk/ns-ntddk-_ps_create_notify_info
https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntddk/nf-ntddk-pssetcreateprocessnotifyroutine
https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-exacquireresourceexclusivelite
https://learn.microsoft.com/en-us/windows-hardware/drivers/kernel/eresource-structures
```

## Schema

Local schema:

```text
docs/plan/srev-100-process-create-caller-snapshot.schema.json
```

The process create caller snapshot contract is:

```text
PS_CREATE_NOTIFY_INFO.ParentProcessId is the inherited parent process and is not necessarily the creator process
PS_CREATE_NOTIFY_INFO.CreatingThreadId.UniqueProcess is the official creator/caller process id for Vista+ create notifications
legacy PsSetCreateProcessNotifyRoutine has only ParentId and current callback context, so it keeps PsGetCurrentProcessId as CallerId
Process_Find with out_irql returns while holding Process_ListLock shared
Process_NotifyProcess_Create must clone parent_proc->box before releasing Process_ListLock
Process_Delete removes and frees PROCESS state only after acquiring Process_ListLock exclusive
the caller/parent selection logic must not dereference parent_proc after Process_ListLock is released
the stale crash wording must be replaced by an explicit stable sandbox-state snapshot contract
```

## Topology

Vista+ path:

```text
PsSetCreateProcessNotifyRoutineEx
  -> Process_NotifyProcessEx
  -> CreateInfo->ParentProcessId
  -> CreateInfo->CreatingThreadId.UniqueProcess
  -> Process_NotifyProcess_Create(ProcessId, ParentId, CallerId, ...)
```

Legacy XP path:

```text
PsSetCreateProcessNotifyRoutine
  -> Process_NotifyProcess
  -> ParentId
  -> PsGetCurrentProcessId()
  -> Process_NotifyProcess_Create(ProcessId, ParentId, CallerId, ...)
```

Parent state snapshot:

```text
Process_Find(CallerId or ParentId, &irql)
  -> Process_ListLock held shared
  -> parent_proc->box is cloned while pointer is stable
  -> release Process_ListLock
  -> later code uses cloned BOX, not parent_proc

Process_Delete
  -> acquire Process_ListLock exclusive
  -> remove PROCESS from Process_Map
  -> release Process_ListLock
  -> free PROCESS pool
```

## Logic Risk

The old comment was directionally useful but too imprecise: it described a
possible failure outcome instead of the legal lifetime contract. The actual
contract is that a borrowed `PROCESS *` from `Process_Find(..., &irql)` is valid
only while `Process_ListLock` remains held. Any process sandbox state needed
after that point must be copied into caller-owned memory first.

For Vista+ notifications, the official creator id should come from
`CreateInfo->CreatingThreadId.UniqueProcess`. Relying on current callback
context is documented as equivalent for this callback path, but it is an
indirect inference where the official data structure already provides the
identity edge.

## Fix

`Process_NotifyProcessEx` now passes `CreateInfo->CreatingThreadId.UniqueProcess`
as `CallerId` to `Process_NotifyProcess_Create`. The legacy XP notify path keeps
`PsGetCurrentProcessId()` because that callback shape has no
`PS_CREATE_NOTIFY_INFO`.

The stale comment was rewritten from a crash-outcome statement into the stable
sandbox-state snapshot contract. The process-list lock topology and
`Box_Clone` timing are unchanged.

## Acceptance Gate

`docs/plan/check-srev-100.py` validates the draft-07 schema, official
references, Vista+ caller identity source, legacy caller identity preservation,
`Process_Find` shared-lock return shape, parent box clone before
`Process_ListLock` release, `Process_Delete` exclusive removal/free topology,
stale crash wording removal, and ledger entry. `docs/plan/check-srev-100.sh` is
the matrix wrapper.

Runtime gate: Windows process-create matrix with ordinary parent create,
explicit parent-process attribute create, AppInfo/RuntimeBroker-style delegated
create, sandboxed caller with non-sandbox inherited parent, non-sandbox caller
with sandbox inherited parent, rapid parent exit during child creation, and
Driver Verifier observation for process-list lock balance.
