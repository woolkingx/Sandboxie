# SREV-141: Object Callback KernelHandle Boundary

## Stage Gate

| Field | Value |
|---|---|
| Stage | action |
| Input artifact | `Sandboxie/core/drv/obj_flt.c`, `Sandboxie/core/drv/thread.c`, `Sandboxie/core/drv/thread.h`, SREV-015 and SREV-138 ALPC/IPC precedent, Microsoft Object Manager callback references |
| Output artifact | `docs/plan/srev-141-obj-callback-kernelhandle-boundary.schema.json`, `docs/plan/check-srev-141.py`, `docs/plan/check-srev-141.sh`, ledger fragment |
| Owner | `Sandboxie/core/drv/obj_flt.c` process/thread handle pre-operation callback |
| Acceptance gate | source checker plus full SREV/KPATH/core coverage matrix; Windows runtime proof remains required for process/thread handle policy behavior |

## Evidence

`Sandboxie/core/drv/obj_flt.c` was the highest-ranked unnamed reviewable core
file after SREV-140. It registers an Object Manager pre-operation callback for
`PsProcessType` and `PsThreadType`, for both `OB_OPERATION_HANDLE_CREATE` and
`OB_OPERATION_HANDLE_DUPLICATE`. The callback reads the operation-specific
`DesiredAccess` field, passes the initial mask to
`Thread_CheckObject_CommonEx`, and writes the returned mask back before the
handle operation completes.

The file also has a historical comment block that lists other object classes
handled elsewhere: files by the file minifilter, registry keys by registry
callbacks, token/process/thread checks by thread/token policy, and ports by IPC
syscall filtering. The same block says proper IPC isolation requires filtering
`NtRequestPort`, `NtRequestWaitReplyPort`, and
`NtAlpcSendWaitReceivePort`. That statement is correct topology: Object Manager
process/thread handle callbacks do not parse LPC/ALPC message payloads.

Before this SREV, the callback gate comment said "Filter only if request made
outside of the kernel" and kept a commented-out `ExGetPreviousMode` check, while
the active condition was `PreInfo->KernelHandle == 1`. Microsoft documents
`KernelHandle` as a bit that says whether the handle itself is a kernel handle.
Microsoft documents `ExGetPreviousMode` separately as the previous processor
mode for the current thread. Those are not the same schema field. The code's
active behavior is a kernel-handle skip, not a previous-mode gate.

Official references:

- https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-obregistercallbacks
- https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/ns-wdm-_ob_callback_registration
- https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/ns-wdm-_ob_operation_registration
- https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/ns-wdm-_ob_pre_operation_information
- https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/ns-wdm-_ob_pre_create_handle_information
- https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/ns-wdm-_ob_pre_duplicate_handle_information
- https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-exgetpreviousmode

## Data

`Obj_CallbackRegistration`, `Obj_OperationRegistrations[2]`,
`Driver_Altitude`, `Obj_FilterCookie`, `Obj_CallbackInstalled`,
`PreInfo->Operation`, `PreInfo->KernelHandle`, `PreInfo->Object`,
`PreInfo->ObjectType`, `CreateHandleInformation.DesiredAccess`,
`DuplicateHandleInformation.DesiredAccess`, `PsProcessType`, `PsThreadType`,
`PsGetProcessId`, `PsGetThreadProcessId`, `PsGetThreadProcess`, and
`Thread_CheckObject_CommonEx`.

## Schema

`OBJ_CALLBACK_KERNELHANDLE_BOUNDARY` says:

- `obj_flt.c` owns only Object Manager process/thread handle pre-operation
  filtering.
- `ObRegisterCallbacks` registration is limited to the object types and
  operations declared in `OB_OPERATION_REGISTRATION`.
- The local registration has exactly two object-type entries:
  `PsProcessType` and `PsThreadType`.
- `KernelHandle` means the target handle is a kernel handle. It is not a
  previous-mode field and must not be documented as an `ExGetPreviousMode`
  substitute.
- Non-kernel process/thread handle callbacks must flow to
  `Thread_CheckObject_CommonEx` so policy can remove rights from
  `DesiredAccess`.
- The pre-operation callback may restrict the granted access by modifying
  `DesiredAccess`; it must not add rights beyond the requested mask.
- IPC message isolation is outside this callback and remains owned by the
  IPC/LPC/ALPC hook and endpoint-filter surfaces.

## Topology

Legal process/thread handle flow:

```text
Object Manager process/thread handle create or duplicate
  -> Obj_PreOperationCallback
  -> skip only if PreInfo->KernelHandle is set
  -> select CreateHandleInformation or DuplicateHandleInformation DesiredAccess
  -> Thread_CheckObject_CommonEx
  -> write restricted DesiredAccess back
  -> Object Manager grants the reduced access mask
```

Out-of-scope IPC flow:

```text
NtRequestPort / NtRequestWaitReplyPort / NtAlpcSendWaitReceivePort
  -> DLL/syscall/driver IPC surfaces
  -> PORT_MESSAGE or ALPC payload parsing
  -> endpoint policy
```

Those IPC operations are not process/thread handle open or duplicate operations,
so this Object Manager callback is not their parser or policy owner.

## Logic Risk

The stale previous-mode comment is small, but the consequence is not cosmetic:
future edits could change the skip gate to `ExGetPreviousMode() == KernelMode`
under the mistaken belief that this matches the current behavior. That would
silently change the callback boundary from "skip kernel handles" to "skip
kernel-mode callers", which is a different Windows schema axis. The correct
source action is to align the comment with the active `KernelHandle` contract,
then preserve the deeper policy/runtime proof as a Windows gate.

The IPC caveat in the file is also important. It should not be "fixed" by
trying to register unsupported Object Manager callback object types. Microsoft
documents `OB_OPERATION_REGISTRATION.ObjectType` support for process, thread,
and desktop handle operations. The correct route for port send/wait isolation
is the existing LPC/ALPC syscall and endpoint-filter topology documented by
SREV-015, SREV-138, and KPATH-006.

## Fix

`obj_flt.c` now describes the active gate as a kernel-handle skip and removes
the dead commented-out `ExGetPreviousMode` branch. The executable policy is
unchanged: non-kernel process/thread handle create and duplicate operations
still pass through `Thread_CheckObject_CommonEx`, and kernel handles still
return `OB_PREOP_SUCCESS` immediately.

## Acceptance Gate

`docs/plan/check-srev-141.py` validates the draft-07 schema, official reference
links, Object Manager registration shape, the corrected source comment,
process/thread `DesiredAccess` routing through `Thread_CheckObject_CommonEx`,
IPC caveat preservation, related ALPC/IPC precedent, and the ledger fragment.
`docs/plan/check-srev-141.sh` is the matrix wrapper.

Runtime/build gate: Windows driver build; open/duplicate process and thread
handles from a sandboxed process and host process; prove sandbox policy removes
write/read-sensitive rights from non-kernel process/thread handles; prove
kernel-handle callback paths still avoid policy mutation; verify IPC/ALPC
message isolation remains covered by the IPC syscall/filter tests rather than
this Object Manager callback.
