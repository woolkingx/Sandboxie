# SREV-342: Token Primary Kernel Handle Boundary

| Field | Content |
|---|---|
| Stage | schema -> topology -> verify |
| Input artifact | `Sandboxie/core/drv/token.c`, Microsoft `ObOpenObjectByPointer`, `ObReferenceObjectByHandle`, Driver Verifier miscellaneous checks, and process access rights documentation |
| Output artifact | Source comment owner, draft-07 schema, checker, and ledger fragment |
| Owner | `Token_AssignPrimary` / `Token_AssignPrimaryHandle` primary-token replacement handle boundary |
| Acceptance gate | Targeted checker validates official references, token object to kernel-handle edge, `PROCESS_ACCESS_TOKEN` consumption, process handle kernel handle edge, stale Driver Verifier crash wording removal, and ledger fragment |

## Data

`Token_AssignPrimary` receives a token object pointer. It opens that token object
with:

```text
ObOpenObjectByPointer(TokenObject, OBJ_KERNEL_HANDLE, ..., KernelMode, &TokenHandle)
```

It then calls `Token_AssignPrimaryHandle`, which opens a process object with
`OBJ_KERNEL_HANDLE`, temporarily clears local process-token-freeze state when
needed, and passes the token handle through a `PROCESS_ACCESS_TOKEN` buffer to:

```text
ZwSetInformationProcess(ProcessHandle, ProcessAccessToken, &info, sizeof(info))
```

The old comment only said Windows 7 Driver Verifier would crash if the token
handle was not a kernel handle. The actual local invariant is that the token
object pointer to handle conversion is owned by `Token_AssignPrimary`, and
`Token_AssignPrimaryHandle` must receive a kernel-only token handle for the
`ProcessAccessToken` operation.

## Official Shape

Microsoft documents `ObOpenObjectByPointer` as opening an object pointer and
returning a handle. If the caller is not running in the system process context,
the handle attributes must include `OBJ_KERNEL_HANDLE`; otherwise the handle can
be accessed by the current process. The returned handle must eventually be
released with `ZwClose`.

Microsoft documents `ObReferenceObjectByHandle` as validating a handle and
returning the referenced object pointer. Starting with Windows 7, Driver
Verifier issues a bug check when `AccessMode` is `KernelMode` and a handle
received from user address space is used.

Microsoft documents Driver Verifier miscellaneous checks as including incorrect
kernel-handle references and invalid kernel handles beginning with Windows 7.

Microsoft documents `PROCESS_SET_INFORMATION` as the process right required to
set certain process information. No public Microsoft Learn page was found for
the private `ZwSetInformationProcess(ProcessAccessToken)` / `PROCESS_ACCESS_TOKEN`
ABI shape during this SREV, so that wire shape remains a Windows runtime gate.

Official references:

- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/nf-ntifs-obopenobjectbypointer`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-obreferenceobjectbyhandle`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/devtest/miscellaneous-checks`
- `https://learn.microsoft.com/en-us/windows/win32/procthread/process-security-and-access-rights`

## Boundary

```text
TokenObject pointer
  -> Token_AssignPrimary
  -> ObOpenObjectByPointer(... OBJ_KERNEL_HANDLE ..., KernelMode, &TokenHandle)
  -> Token_AssignPrimaryHandle
  -> PROCESS_ACCESS_TOKEN.Token = TokenKernelHandle
  -> ZwSetInformationProcess(ProcessHandle, ProcessAccessToken, ...)
  -> ZwClose(TokenHandle)
```

The source comment belongs at the consumer boundary, but the owner edge starts
in `Token_AssignPrimary`, where the token object pointer becomes a kernel-only
handle.

## Topology

```text
Token_AssignPrimary
  -> ObOpenObjectByPointer(TokenObject, OBJ_KERNEL_HANDLE, KernelMode)
  -> TokenHandle
  -> Token_AssignPrimaryHandle(ProcessObject, TokenHandle, SessionId)
  -> ObOpenObjectByPointer(ProcessObject, OBJ_KERNEL_HANDLE, KernelMode)
  -> PROCESS_ACCESS_TOKEN info { TokenKernelHandle, NULL thread }
  -> ZwSetInformationProcess(ProcessAccessToken)
  -> restore PrimaryTokenFrozen
  -> ZwClose(ProcessHandle)
  -> ZwClose(TokenHandle)
```

## Logic Risk

The old comment was accurate but too narrow. It framed the invariant as a
Windows 7 Driver Verifier crash avoidance note, not as a handle-owner boundary.
Future edits could pass a user-visible token handle into `Token_AssignPrimaryHandle`
or move token-handle creation away from the `OBJ_KERNEL_HANDLE` edge without
noticing that `ProcessAccessToken` consumes a kernel-only handle in this local
topology.

## Fix

Comment-only source clarification. The source now names SREV-342 and says
`ProcessAccessToken` consumes a kernel-only token handle; `Token_AssignPrimary`
opens `TokenObject` with `OBJ_KERNEL_HANDLE`; and that owner boundary must stay
paired with `ZwSetInformationProcess` and Driver Verifier's kernel-handle
checks. No handle attribute, access mode, process-token replacement behavior,
frozen-bit handling, mitigation flag write, status logging, or close behavior
changed.

## Acceptance Gate

`docs/plan/check-srev-342.py` validates the draft-07 schema, official
references, token object to `OBJ_KERNEL_HANDLE` edge, process object to
`OBJ_KERNEL_HANDLE` edge, `PROCESS_ACCESS_TOKEN` consumer, `ZwClose` cleanup,
stale Driver Verifier crash wording removal, combined ledger entry, and split
ledger fragment.

Runtime gate: Windows driver build and VM matrix with Driver Verifier
miscellaneous checks on Windows 7/10/11 for primary-token replacement,
confirming the token and process handles stay kernel-only, rejected
`ZwSetInformationProcess(ProcessAccessToken)` paths close both handles, and
normal sandbox primary-token replacement still works.
