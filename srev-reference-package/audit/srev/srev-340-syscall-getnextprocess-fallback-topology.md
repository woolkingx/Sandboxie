# SREV-340: Syscall GetNextProcess Fallback Topology

| Field | Content |
|---|---|
| Stage | perceive -> schema -> topology -> verify |
| Input artifact | `Sandboxie/core/drv/syscall_open.c`, `Sandboxie/core/drv/syscall.c`, SREV-045, Microsoft `ObRegisterCallbacks`, `OB_PRE_CREATE_HANDLE_INFORMATION`, process access rights, and `ObReferenceObjectByHandle` documentation |
| Output artifact | Source comment owner, draft-07 schema, checker, and ledger fragment |
| Owner | `Syscall_GetNextProcess` fallback process-handle enumeration path |
| Acceptance gate | Targeted checker validates official references, public-doc gap for `NtGetNextProcess`, ObCallback bypass, fallback loop topology, rejected-handle close, SREV-045 writeback adjacency, stale TODO removal, and ledger fragment |

## Data

`Syscall_GetNextProcess` protects the `NtGetNextProcess` style enumeration path
when `Obj_CallbackInstalled` is false. The source comment says the syscall can
be used inside the sandbox to get writable handles to outside-box processes.

The local fallback route:

- allows direct native dispatch when object callbacks are installed;
- redirects the output handle through the same temporary TLS slot shape used by
  SREV-045;
- invokes the native syscall;
- restores the temporary slot and closes a rejected old enumeration handle;
- references the returned process handle as `*PsProcessType`;
- checks access through `Thread_CheckObject_Common`;
- if the returned process is not allowed, stores that handle as the old handle
  and loops to ask for the next process;
- on acceptance, writes the restored handle back through
  `Syscall_WriteRestoredHandleToUser`.

## Official Shape

Microsoft documents `ObRegisterCallbacks` as registering callbacks for thread,
process, and desktop handle operations. That is the local reason the
`Obj_CallbackInstalled` path can defer process-handle filtering to callbacks.

Microsoft documents `OB_PRE_CREATE_HANDLE_INFORMATION.DesiredAccess` as the
access to grant for a process or thread handle. The pre-operation callback may
remove listed rights and cannot add rights beyond the original request.

Microsoft documents process access rights such as `PROCESS_CREATE_THREAD`,
`PROCESS_DUP_HANDLE`, `PROCESS_VM_OPERATION`, `PROCESS_VM_READ`, and
`PROCESS_VM_WRITE` as process-specific rights. It also warns that some rights can
be used to gain other access, for example `PROCESS_DUP_HANDLE`.

Microsoft documents `ObReferenceObjectByHandle` as validating a handle for an
object type and returning a referenced object pointer plus optional handle
information.

No public Microsoft Learn DDI page for `NtGetNextProcess` was found during this
SREV. Therefore this entry does not claim a public official syscall ABI shape;
the syscall parameter ABI and enumeration semantics remain a Windows runtime
gate.

Official references:

- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-obregistercallbacks`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/ns-wdm-_ob_pre_create_handle_information`
- `https://learn.microsoft.com/en-us/windows/win32/procthread/process-security-and-access-rights`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-obreferenceobjectbyhandle`

## Boundary

```text
GetNextProcess syscall args
  -> if ObCallbacks installed: native syscall owns process-handle filtering
  -> else: temporary TLS output handle
  -> Syscall_Invoke
  -> ObReferenceObjectByHandle(NewHandle, *PsProcessType)
  -> Thread_CheckObject_Common
  -> denied: set old handle to NewHandle and loop
  -> accepted: Syscall_WriteRestoredHandleToUser
```

`Syscall_GetNextProcess` owns only the fallback filtering loop when process
object callbacks are unavailable. It does not own the private syscall ABI or the
object-callback access-right schema.

## Topology

```text
Obj_CallbackInstalled
  -> Syscall_Invoke

!Obj_CallbackInstalled
  -> Syscall_ReplaceTargetHandle(&user_args[4], TRUE)
  -> Syscall_Invoke
  -> Syscall_RestoreTargetHandle
  -> close previous rejected enumeration handle
  -> ObReferenceObjectByHandle(NewHandle, *PsProcessType)
  -> Thread_CheckObject_Common(proc, ProcessObject, DesiredAccess, TRUE, FALSE)
  -> denied: user_args[0] = NewHandle; goto next
  -> accepted: Syscall_WriteRestoredHandleToUser(UserHandlePtr, NewHandle, orig_status)
```

## Logic Risk

The stale TODO made the fallback look unimplemented even though a filtering loop
exists. The real unresolved part is narrower: the private `NtGetNextProcess`
ABI and Windows runtime enumeration behavior still need a VM matrix. Treating
the TODO as an invitation to rewrite the path without that matrix could break
the rejected-handle closure and restored-handle ownership work from SREV-045.

## Fix

Comment-only source clarification. The source now names SREV-340 and states
that, without object callbacks, Sandboxie enumerates with `NtGetNextProcess`,
closes each rejected outside-box process handle before trying the next one, and
keeps the syscall ABI as a runtime-only gate. No loop condition, handle close,
object reference, access check, writeback, or callback-bypass behavior changed.

## Acceptance Gate

`docs/plan/check-srev-340.py` validates the draft-07 schema, official
references, public-doc gap statement for `NtGetNextProcess`, ObCallback direct
native path, fallback loop topology, rejected-handle close, process-object
reference, `Thread_CheckObject_Common` access check, SREV-045 adjacency, stale
TODO removal, combined ledger entry, and split ledger fragment.

Runtime gate: Windows VM matrix for `NtGetNextProcess` with `Obj_CallbackInstalled`
on/off, denied outside-box writable process handles, accepted same-box handles,
end-of-enumeration status, invalid/racing output pointer from SREV-045, and
handle-leak observation while repeatedly skipping denied processes.
