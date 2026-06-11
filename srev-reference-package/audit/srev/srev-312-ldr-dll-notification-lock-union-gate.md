# SREV-312: Ldr DLL Notification Lock And Union Gate

## Stage Gate

| Field | Value |
|---|---|
| Stage | data -> schema -> topology -> logic -> action -> verify |
| Input artifact | `Sandboxie/core/dll/ldr.c`, Microsoft `LdrRegisterDllNotification`, `LdrDllNotification`, and NTSTATUS documentation |
| Output artifact | Loader notification reason/union contract, draft-07 schema, targeted checker, ledger fragment |
| Owner | `Ldr_LdrDllNotification` |
| Acceptance gate | Targeted checker validates official references, named notification reason constants, loaded/unloaded union member routing, loader-lock success gate before unlock, unchanged callback-table topology, combined ledger, and ledger fragment |

## Data

`Ldr_Init` registers `Ldr_LdrDllNotification` with
`LdrRegisterDllNotification` on Windows 8.1 and later. The callback receives a
notification reason and an `LDR_DLL_NOTIFICATION_DATA` union. It then forwards
load or unload events into Sandboxie's local module callback table through
`Ldr_MyDllCallbackNew`.

Before this SREV, the local callback used raw reason values `1` and `2`,
called `__sys_LdrUnlockLoaderLock` even when `__sys_LdrLockLoaderLock` had not
been proven successful, and the unload branch read `NotificationData->Loaded`
for the image base even though the reason is unload.

## Official Shape

Microsoft documents `LdrRegisterDllNotification` as registering a callback that
is called when a DLL is loaded. The `Flags` parameter must be zero, and success
is returned as `STATUS_SUCCESS`.

Microsoft documents `LdrDllNotification` as receiving
`LDR_DLL_NOTIFICATION_REASON_LOADED` and
`LDR_DLL_NOTIFICATION_REASON_UNLOADED`. Loaded notifications point at
`LDR_DLL_LOADED_NOTIFICATION_DATA`; unloaded notifications point at
`LDR_DLL_UNLOADED_NOTIFICATION_DATA`. Microsoft also warns that it is unsafe for
the notification callback to call functions in any module other than itself.

Microsoft documents NTSTATUS values as success, informational, warning, and
error values, and says callers should use `NT_SUCCESS(Status)` instead of
testing only for `STATUS_SUCCESS`.

Official references:

- `https://learn.microsoft.com/en-us/windows/win32/devnotes/ldrregisterdllnotification`
- `https://learn.microsoft.com/en-us/windows/win32/devnotes/ldrdllnotification`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/kernel/using-ntstatus-values`

## Schema

Local schema:

```text
docs/plan/srev-312-ldr-dll-notification-lock-union-gate.schema.json
```

Contract id:

```text
LDR_DLL_NOTIFICATION_LOCK_UNION_GATE
```

## Topology

```text
Windows loader notification
  -> Ldr_LdrDllNotification(NotificationReason, NotificationData)
  -> loaded reason uses NotificationData->Loaded
  -> unloaded reason uses NotificationData->Unloaded
  -> Ldr_MyDllCallbackNew(ImageName, ImageBase, LoadState)
  -> Ldr_Dlls callback table
  -> owner-specific init/unhook behavior
```

Loader-lock topology:

```text
loaded notification
  -> __sys_LdrLockLoaderLock
  -> NT_SUCCESS(status) gate
  -> local callback dispatch
  -> __sys_LdrUnlockLoaderLock only for the proven acquired cookie
```

## Logic Risk

The old code trusted the loader-lock call without checking the NTSTATUS shape.
If that call ever failed, the callback could still call
`__sys_LdrUnlockLoaderLock` with an unowned or meaningless cookie. The old unload
branch also used the loaded union member for the image base, hiding the legal
reason-to-union edge even though the two local structures currently have the
same fields.

The callback still performs Sandboxie-specific module dispatch from a loader
notification. This SREV does not redesign that broader loader-callback policy;
it only makes the current crossing explicit and prevents an unlock without a
successful lock.

## Fix

`ldr.c` now names the documented notification reason values with local
constants. The loaded branch tests `NT_SUCCESS(status)` before calling the local
module callback and before unlocking the loader lock. The unloaded branch now
uses `NotificationData->Unloaded.DllBase` with
`NotificationData->Unloaded.BaseDllName`.

No `Ldr_Dlls` callback registration, `DllSkipHook`, module init function,
module unhook, image tracing, or ARM64 hook policy changed.

## Acceptance Gate

`docs/plan/check-srev-312.py` validates the draft-07 schema, official
references, source constants, loaded/unloaded union routing, loader-lock
success gate before unlock, removal of raw reason dispatch in the callback,
unchanged callback-table topology, combined ledger entry, and split ledger
fragment.

Runtime gate: Windows 8.1+ DLL load/unload smoke with a module that loads and
unloads inside a sandboxed process, plus ARM64/ARM64EC regression proof that the
notification callback does not reintroduce the known loader hang class.
