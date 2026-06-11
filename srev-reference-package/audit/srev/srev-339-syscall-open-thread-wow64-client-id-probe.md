# SREV-339: Syscall OpenThread WOW64 ClientId Probe

| Field | Content |
|---|---|
| Stage | schema -> boundary -> topology -> action -> verify |
| Input artifact | `Sandboxie/core/drv/syscall_open.c`, `Sandboxie/core/drv/syscall.c`, `Sandboxie/core/drv/process_util.c`, SREV-045, SREV-333, Microsoft `OpenThread`, thread access rights, WOW64 implementation, and `ProbeForRead` documentation |
| Output artifact | Source owner patch, draft-07 schema, checker, and ledger fragment |
| Owner | `Syscall_OpenHandle` OpenThread WOW64 access-mask downgrade gate |
| Acceptance gate | Targeted checker validates official references, `CLIENT_ID` probe-before-read, exception early return, exact access-mask gate, outside-box downgrade, stale HACK wording removal, and ledger fragment |

## Data

`Syscall_OpenHandle` handles multiple open-style syscalls before invoking the
native syscall through `Syscall_Invoke`. For `OpenThread`, one local compatibility
gate recognizes the exact access mask:

```text
THREAD_GET_CONTEXT | THREAD_SET_CONTEXT
```

The gate then inspects the caller-supplied `CLIENT_ID` process id and, when the
target is null or outside the sandbox, removes `THREAD_SET_CONTEXT` before the
native syscall. This preserves the read-context behavior needed by Windows 10
1903+ WOW64 while avoiding a write-context handle to an outside-box thread.

Before this SREV, the gate dereferenced `ClientId->UniqueProcess` directly from
the syscall argument pointer. The outer syscall dispatcher has a broad
try/except, but the local boundary did not document or prove the user-buffer
shape before reading it.

## Official Shape

Microsoft documents `OpenThread` as opening an existing thread object. Its
`dwDesiredAccess` value is checked against the thread object's security
descriptor, and the returned handle is granted access only to the extent
requested by that parameter.

Microsoft documents thread access rights: `THREAD_GET_CONTEXT` is required to
read a thread context, while `THREAD_SET_CONTEXT` is required to write a thread
context.

Microsoft documents WOW64 as the user-mode emulator between 32-bit `Ntdll.dll`
and the native kernel. WOW64 intercepts kernel calls, extracts arguments from
the 32-bit stack, extends them to 64 bits, and makes the native system call.

Microsoft documents `ProbeForRead` as validating that a user-mode buffer is in
the user address range and correctly aligned. It raises exceptions for invalid
range or alignment, and drivers must call it inside a try/except block; later
accesses must also stay inside try/except because user mappings can change.

Official references:

- `https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-openthread`
- `https://learn.microsoft.com/en-us/windows/win32/procthread/thread-security-and-access-rights`
- `https://learn.microsoft.com/en-us/windows/win32/winprog64/wow64-implementation-details`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-probeforread`

## Boundary

```text
Syscall_Api_Invoke
  -> ProbeForRead(user_args, entry->param_count * sizeof(ULONG_PTR))
  -> Syscall_OpenHandle
  -> OpenThread exact access mask
  -> caller-supplied CLIENT_ID pointer
  -> ProbeForRead(CLIENT_ID)
  -> captured UniqueProcess
  -> Process_IsSameBox
  -> optional THREAD_SET_CONTEXT removal
  -> Syscall_Invoke
```

`Syscall_Api_Invoke` owns the syscall argument-vector read. `Syscall_OpenHandle`
owns only the OpenThread-specific access-mask rewrite before native dispatch.
`Process_IsSameBox` owns sandbox membership for a captured process id, not the
user pointer itself.

## Topology

```text
OpenThread + THREAD_GET_CONTEXT|THREAD_SET_CONTEXT
  -> PCLIENT_ID user_args[3]
  -> if non-null, ProbeForRead(CLIENT_ID) inside local try/except
  -> ClientProcessId = ClientId->UniqueProcess
  -> ClientId == NULL or !Process_IsSameBox(proc, NULL, ClientProcessId)
  -> user_args[1] = THREAD_GET_CONTEXT
```

The invalid-pointer path returns `GetExceptionCode()` locally. That keeps the
previous early-failure shape explicit instead of depending on the outer syscall
dispatcher's broad exception handler.

## Logic Risk

The old comment mixed a Windows/WOW64 compatibility observation with an
unproven user-pointer dereference. The real local invariant is narrower:
Sandboxie may reduce the exact WOW64-compatible `OpenThread` access request, but
it must prove the `CLIENT_ID` buffer before reading the target process id used
for the same-box decision.

If future edits read `CLIENT_ID` outside try/except, broaden the access-mask
match, or remove `THREAD_SET_CONTEXT` for same-box targets, the gate can either
turn malformed caller data into a driver exception path or over-apply the WOW64
compatibility downgrade.

## Fix

`Syscall_OpenHandle` now names SREV-339 and the Windows 10 1903+ WOW64
read-context gate. It captures `ClientId->UniqueProcess` only after
`ProbeForRead(ClientId, sizeof(CLIENT_ID), sizeof(ULONG_PTR))` succeeds inside a
local try/except. Probe or read exceptions return `GetExceptionCode()`. The
access-mask match, null-target downgrade, outside-box downgrade, later handle
replacement, object validation, and writeback topology remain unchanged.

## Acceptance Gate

`docs/plan/check-srev-339.py` validates the draft-07 schema, official
references, source comment ownership, exact `OpenThread` and
`THREAD_GET_CONTEXT | THREAD_SET_CONTEXT` gate, `CLIENT_ID` probe-before-read,
captured `ClientProcessId`, local exception return, `Process_IsSameBox` use,
stale HACK wording removal, SREV-045 / SREV-333 adjacency, combined ledger
entry, and split ledger fragment.

Runtime gate: Windows x64 WOW64 smoke on Windows 10 1903+ and current Windows,
covering host-thread read-context behavior, same-box OpenThread
`THREAD_GET_CONTEXT|THREAD_SET_CONTEXT`, outside-box downgrade to
`THREAD_GET_CONTEXT`, null/invalid `CLIENT_ID`, and malformed user pointer
exception status; Driver Verifier should not report unsafe user-buffer access.
