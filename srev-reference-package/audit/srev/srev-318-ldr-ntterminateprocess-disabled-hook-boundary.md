# SREV-318: Ldr NtTerminateProcess Disabled Hook Boundary

## Stage Gate

| Field | Value |
|---|---|
| Stage | data -> schema -> topology -> logic -> action -> verify |
| Input artifact | `Sandboxie/core/dll/ldr.c`, Microsoft `LdrRegisterDllNotification`, `LdrUnregisterDllNotification`, `LdrDllNotification`, and `TerminateProcess` documentation |
| Output artifact | disabled NtTerminateProcess hook boundary, draft-07 schema, targeted checker, ledger fragment |
| Owner | `Ldr_Init` Windows 8.1+ loader notification setup |
| Acceptance gate | Targeted checker validates official references, active notification registration, inactive unregister/NtTerminateProcess hook body, removal of stale TODO/Fix-Me/hang wording, unchanged `Ldr_Win10_LdrLoadDll` hook, SREV-312 adjacency, combined ledger, and ledger fragment |

## Data

On Windows 8.1 and later, `Ldr_Init` resolves
`LdrRegisterDllNotification` and `LdrUnregisterDllNotification` from `ntdll`.
It registers `Ldr_LdrDllNotification` and stores the callback identifier in
`LdrLoaderCookie`. A commented-out `Ldr_NtTerminateProcess` block would
unregister the notification callback through `LdrLoaderCookie` when the current
process terminates, but that hook is not active. The active hook in this block
is still `Ldr_Win10_LdrLoadDll`.

Before this SREV, the inactive `NtTerminateProcess` hook line had only a
`Todo: Fix-Me` comment stating that it hangs some ARM64 processes. That symptom
wording did not name the official cookie owner or the runtime gate required
before anyone can enable the hook.

## Official Shape

Microsoft documents `LdrRegisterDllNotification` as registering a DLL load
notification callback and returning a callback identifier cookie. The `Flags`
parameter must be zero. The cookie is the identifier used to unregister the
callback.

Microsoft documents `LdrUnregisterDllNotification` as cancelling a DLL load
notification previously registered by `LdrRegisterDllNotification`, using the
cookie returned by the registration call. It returns `STATUS_SUCCESS` when the
unregister succeeds and `STATUS_DLL_NOT_FOUND` when the callback is not found.

Microsoft documents `LdrDllNotification` as being called before dynamic linking
takes place and warns that it is unsafe for the notification callback to call
functions in any module other than itself.

Microsoft documents `TerminateProcess` as unconditional process termination.
It stops all threads in the target process, may compromise DLL-maintained global
state compared with `ExitProcess`, and is asynchronous for a process other than
the caller.

Official references:

- `https://learn.microsoft.com/en-us/windows/win32/devnotes/ldrregisterdllnotification`
- `https://learn.microsoft.com/en-us/windows/win32/devnotes/ldrunregisterdllnotification`
- `https://learn.microsoft.com/en-us/windows/win32/devnotes/ldrdllnotification`
- `https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-terminateprocess`

## Schema

Local schema:

```text
docs/plan/srev-318-ldr-ntterminateprocess-disabled-hook-boundary.schema.json
```

Contract id:

```text
LDR_NTTERMINATEPROCESS_DISABLED_HOOK_BOUNDARY
```

## Topology

Active topology:

```text
Windows 8.1+ process
  -> Ldr_Init
  -> GetProcAddress("LdrRegisterDllNotification")
  -> GetProcAddress("LdrUnregisterDllNotification")
  -> LdrRegisterDllNotification(..., &LdrLoaderCookie)
  -> Ldr_LdrDllNotification
  -> SREV-312 loader notification dispatch
  -> SBIEDLL_HOOK(Ldr_Win10_, LdrLoadDll)
```

Disabled topology:

```text
NtTerminateProcess hook
  -> Ldr_NtTerminateProcess
  -> current-process termination gate
  -> LdrUnregisterDllNotification(LdrLoaderCookie)
  -> native NtTerminateProcess
```

The disabled topology is not active source behavior today.

Adjacent owner contract:

- SREV-312: `LDR_DLL_NOTIFICATION_LOCK_UNION_GATE`
- SREV-312 runtime adjacency: Windows 8.1+ DLL load/unload smoke plus ARM64/ARM64EC

## Logic Risk

The old TODO made the risk look like a vague ARM64 problem instead of a
loader-notification lifetime boundary. Enabling the hook would cross three
high-risk edges at once: process termination, notification-cookie unregister,
and the loader-callback environment that Microsoft warns is constrained. The
correct next step is ARM64/ARM64EC process-exit runtime proof and call capture,
not simply uncommenting the hook.

## Fix

Comment-only source clarification. The disabled `NtTerminateProcess` hook is
now labeled as SREV-318 notification-cookie cleanup that remains disabled until
ARM64 process-exit runtime proof exists. No `LdrRegisterDllNotification`,
`LdrUnregisterDllNotification`, `LdrLoaderCookie`, disabled
`Ldr_NtTerminateProcess` body, `NtTerminateProcess` hook, or
`Ldr_Win10_LdrLoadDll` hook behavior changed.

## Acceptance Gate

`docs/plan/check-srev-318.py` validates the draft-07 schema, official
references, active notification registration, inactive unregister and
`NtTerminateProcess` hook body, updated source comment, stale TODO/Fix-Me/hang
wording removal from the hook-selection block, unchanged `Ldr_Win10_LdrLoadDll`
hook, SREV-312 adjacency, combined ledger entry, and split ledger fragment.

Runtime gate: Windows ARM64/ARM64EC process-exit matrix before enabling the
disabled hook: normal self-exit, `TerminateProcess` self-termination,
out-of-process termination, DLL load/unload during shutdown, and negative
controls proving no process hang and no loader notification regression.
