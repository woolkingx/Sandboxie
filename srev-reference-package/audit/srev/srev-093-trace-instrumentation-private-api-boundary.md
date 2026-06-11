# SREV-093: Trace Instrumentation Private API Boundary

## Data

`Sandboxie/core/dll/trace.c` owns the optional `CallTraceEx` syscall tracing
path. The comment-admitted shape is:

```text
CallTraceEx config
ProcessInstrumentationCallback private process-information class
PROCESS_INSTRUMENTATION_CALLBACK_INFORMATION local struct
NtSetInformationProcess
SeDebugPrivilege / token privilege state
x86 / WOW64 / x64 / ARM64 / ARM64EC callback ABI
RtlCaptureContext / RtlRestoreContext context handoff
```

## Official Shape

Microsoft documents public `SetProcessInformation` as accepting only documented
`PROCESS_INFORMATION_CLASS` values such as memory priority, power throttling,
leap-second information, and prefetch override. It requires
`PROCESS_SET_INFORMATION` access on the process handle.

Microsoft documents `NtQueryInformationProcess` and its returned structures as
internal to the operating system and subject to change. Microsoft recommends
public alternatives where available and says dynamic linking is needed if the
internal function is used. The public documentation does not define
`ProcessInstrumentationCallback` or
`PROCESS_INSTRUMENTATION_CALLBACK_INFORMATION` as a stable user-mode contract.

Microsoft documents `AdjustTokenPrivileges` as enabling, disabling, or removing
privileges already present in a token. It cannot add privileges to the token and
callers must check `GetLastError` for `ERROR_NOT_ALL_ASSIGNED`.
In short: AdjustTokenPrivileges cannot add privileges that the token does not
already contain.

Microsoft documents `SeDebugPrivilege` as the debug-programs user right and a
high-trust privilege. The process access-rights documentation separately says
`PROCESS_SET_INFORMATION` is the right used to set certain process information
and that `SeDebugPrivilege` is required for full access to another process, not
as a public contract for this private instrumentation class on the current
process.

Microsoft documents Arm64EC as a Windows 11 ABI that interoperates with x64 code
by following x64 software conventions, while Arm64 uses different conventions.
The Arm64EC ABI documentation describes thunk/checker behavior across x64 and
Arm64EC code, so an ARM64 native callback/restore path is not automatically a
valid Arm64EC instrumentation ABI.

Microsoft documents `RtlCaptureContext` as capturing processor-specific register
state into a `CONTEXT`, and `RtlRestoreContext` as restoring a caller context
from a `CONTEXT`.

```text
https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-setprocessinformation
https://learn.microsoft.com/en-us/windows/win32/api/winternl/nf-winternl-ntqueryinformationprocess
https://learn.microsoft.com/en-us/windows/win32/procthread/process-security-and-access-rights
https://learn.microsoft.com/en-us/windows/win32/api/securitybaseapi/nf-securitybaseapi-adjusttokenprivileges
https://learn.microsoft.com/en-us/windows/win32/secauthz/privilege-constants
https://learn.microsoft.com/en-us/windows-hardware/drivers/debugger/debug-privilege
https://learn.microsoft.com/en-us/windows/arm/arm64ec
https://learn.microsoft.com/en-us/windows/arm/arm64ec-abi
https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/nf-ntifs-rtlcapturecontext
https://learn.microsoft.com/en-us/windows/win32/api/winnt/nf-winnt-rtlrestorecontext
```

## Schema

Local schema:

```text
docs/plan/srev-093-trace-instrumentation-private-api-boundary.schema.json
```

The trace instrumentation contract is:

```text
CallTraceEx may request a process instrumentation callback only through the trace owner
ProcessInstrumentationCallback is a private NtSetInformationProcess class in this tree
public SetProcessInformation documentation does not define the instrumentation callback class
pre-10041 privilege behavior must stay fail-closed until proven by runtime matrix
AdjustTokenPrivileges cannot add SeDebugPrivilege to a token that lacks it
driver-mediated privilege or temporary privilege enablement is not a source-only fix
ARM64EC is not covered by the native ARM64 callback restore path
```

## Topology

Current supported topology:

```text
CallTraceEx config
  -> Trace_Init
  -> InstallInstrumentationCallback
  -> local PROCESS_INSTRUMENTATION_CALLBACK_INFORMATION
  -> NtSetInformationProcess(ProcessInstrumentationCallback)
  -> InstrumentationCallbackAsm
  -> InstrumentationCallback
  -> InstrumentationTrace
```

Current fail-closed topology:

```text
x86 / WOW64 before build 10041 -> STATUS_NOT_SUPPORTED
any architecture before build 10041 -> STATUS_PRIVILEGE_NOT_HELD
ARM64EC -> STATUS_NOT_SUPPORTED
```

The private process-information class is locally declared in
`Sandboxie/common/win32_ntddk.h`. That local header is compatibility input, not
Microsoft's public API source of truth.

## Logic Risk

The old TODO named two tempting fixes: ask SbieDrv to help, or enable a
privilege in compartment-type boxes. Both are unsafe as direct source patches.
The public API shape does not define the instrumentation callback class, and the
public privilege APIs do not let a process add a missing debug privilege. A
driver-mediated path would also cross a kernel/user trust boundary and needs a
wire schema, policy owner, and Windows build matrix before it can be legal.

For ARM64EC, the existing native ARM64 callback restore path cannot be assumed
to fit. Arm64EC is deliberately x64-compatible and thunked, while native ARM64
uses a different ABI.

## Fix

Comment-only source clarification. The source now states that
`ProcessInstrumentationCallback` is a private `NtSetInformationProcess` class,
that pre-10041 behavior stays fail-closed until runtime evidence proves a legal
driver-mediated or temporary privilege-enable path, and that ARM64EC is not
covered by the native ARM64 callback restore path.

No behavior was changed.

## Acceptance Gate

`docs/plan/check-srev-093.py` validates the draft-07 schema, official references,
private API classification, local enum ownership, pre-10041 fail-closed behavior,
ARM64EC fail-closed behavior, removal of the stale TODO wording, and ledger
entry. `docs/plan/check-srev-093.sh` is the matrix wrapper.

Runtime gate: Windows runtime matrix across Windows 7/8.1/10 build 10041+,
x86/WOW64/x64/ARM64/ARM64EC, current-process versus driver-mediated setup, token
privilege state, HVCI on/off where applicable, and `CallTraceEx` logging
correctness. No driver or privilege change is allowed before that matrix exists.
