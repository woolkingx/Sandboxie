---
kind: srev-ledger-entry
id: SREV-312
title: Ldr DLL Notification Lock And Union Gate
status: patched source-level after official LdrRegisterDllNotification, LdrDllNotification, and NTSTATUS shape; needs Windows runtime proof
owner: Sandboxie/core/dll/ldr.c
spec: docs/plan/srev-312-ldr-dll-notification-lock-union-gate.md
schema: docs/plan/srev-312-ldr-dll-notification-lock-union-gate.schema.json
checker: docs/plan/check-srev-312.py
runtime_gate: Windows 8.1+ DLL load/unload smoke plus ARM64/ARM64EC loader notification regression proof
---

### SREV-312: Ldr DLL Notification Lock And Union Gate

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official `LdrRegisterDllNotification`, `LdrDllNotification`, and NTSTATUS shape; needs Windows runtime proof |
| Evidence | `Ldr_Init` registers `Ldr_LdrDllNotification` with `LdrRegisterDllNotification` on Windows 8.1 and later. The callback receives a notification reason plus an `LDR_DLL_NOTIFICATION_DATA` union and forwards load/unload events into `Ldr_MyDllCallbackNew`. Before this SREV, the loaded branch called `__sys_LdrUnlockLoaderLock` without proving `__sys_LdrLockLoaderLock` succeeded, and the unloaded branch read the image base through `NotificationData->Loaded.DllBase` instead of the unload union member. |
| Data | `LdrRegisterDllNotification`, `LdrDllNotification`, `LDR_DLL_NOTIFICATION_REASON_LOADED`, `LDR_DLL_NOTIFICATION_REASON_UNLOADED`, `LDR_DLL_NOTIFICATION_DATA`, `Loaded.BaseDllName`, `Loaded.DllBase`, `Unloaded.BaseDllName`, `Unloaded.DllBase`, `__sys_LdrLockLoaderLock`, `__sys_LdrUnlockLoaderLock`, `NT_SUCCESS`, `Ldr_MyDllCallbackNew`, and `Ldr_Dlls`. |
| Schema | `LDR_DLL_NOTIFICATION_LOCK_UNION_GATE` says `Ldr_LdrDllNotification` owns Windows loader notification reason dispatch; loaded notifications route only through `NotificationData->Loaded`; unloaded notifications route only through `NotificationData->Unloaded`; `LdrLockLoaderLock` status must be tested with `NT_SUCCESS` before unlocking its cookie; this SREV does not change `Ldr_Dlls` callback table policy. |
| Topology | `Windows loader notification -> Ldr_LdrDllNotification -> reason-specific union member -> Ldr_MyDllCallbackNew -> Ldr_Dlls callback table -> owner-specific init/unhook behavior`. Loaded notifications now gate local dispatch and unlock behind a successful loader-lock acquisition. |
| Logic Risk | Unlocking an unproven loader-lock cookie is an invalid ownership edge if the lock call fails. Reading the loaded union member on an unload reason also hides the documented reason-to-data contract, even though the local loaded and unloaded structures currently share field layout. |
| Official Shape | Microsoft documents `LdrRegisterDllNotification` as the DLL-load notification registration API and documents `LdrDllNotification` loaded and unloaded reasons with separate loaded/unloaded notification data. Microsoft documents NTSTATUS success testing through `NT_SUCCESS(Status)`. |
| Fix | `ldr.c` now names the loaded/unloaded notification reason values, tests `NT_SUCCESS(status)` before calling local load dispatch and before unlocking the loader lock, and uses `NotificationData->Unloaded.DllBase` for unloaded notifications. No `Ldr_Dlls` callback registration, `DllSkipHook`, module init function, module unhook, image tracing, or ARM64 hook policy changed. |
| Acceptance Gate | `docs/plan/check-srev-312.py` validates the draft-07 schema, official references, source constants, loaded/unloaded union routing, loader-lock success gate before unlock, removal of raw reason dispatch in the callback, unchanged callback-table topology, combined ledger entry, and split ledger fragment; `docs/plan/check-srev-312.sh` is the targeted wrapper. Runtime gate: Windows 8.1+ DLL load/unload smoke plus ARM64/ARM64EC loader notification regression proof. |
