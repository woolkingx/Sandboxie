# SREV-004 Taskbar AppUserModelID Process-Parameter Workaround

Status: source-level spec before patch.

## Official Shape

Microsoft documents `SetCurrentProcessExplicitAppUserModelID` as the public API
for assigning an explicit AppUserModelID to the current process. It should be
called during initial startup before UI or Jump List manipulation.

Microsoft documents AppUserModelIDs as the taskbar grouping identity for
processes, windows, shortcuts, and file associations. Virtualization or host
process environments may need to assign different AppUserModelIDs to managed
applications.

Microsoft documents `PEB` and `RTL_USER_PROCESS_PARAMETERS` as internal
operating-system structures whose layout may change. Most fields are reserved
for internal use. The public `RTL_USER_PROCESS_PARAMETERS` shape exposes only
`ImagePathName` and `CommandLine`, not `WindowFlags`.

Sources:

- https://learn.microsoft.com/en-us/windows/win32/api/shobjidl_core/nf-shobjidl_core-setcurrentprocessexplicitappusermodelid
- https://learn.microsoft.com/en-us/windows/win32/shell/appids
- https://learn.microsoft.com/en-us/windows/win32/api/winternl/ns-winternl-peb
- https://learn.microsoft.com/en-us/windows/win32/api/Winternl/ns-winternl-rtl_user_process_parameters

## Local Shape

Sandboxie already hooks `SetCurrentProcessExplicitAppUserModelID` so sandboxed
processes get box-aware AppUserModelIDs.

The previous workaround cleared `ProcessParms->WindowFlags &= ~0x5000` before
calling the real Shell API because the source comment reports a crash when the
real API frees `WindowTitle`. The local `RTL_USER_PROCESS_PARAMETERS` structure
comes from `common/win32_ntddk.h`, not from a stable Microsoft public contract.

## Local Risk

Clearing `0x5000` permanently avoids the immediate crash but leaves process
parameters mutated after the Shell API returns. That creates durable drift in
an internal OS-owned structure and can leak or misrepresent `WindowTitle`
ownership for later code.

Fully replacing this with documented APIs is not possible from current local
evidence because the crash is specifically inside the real Shell API's handling
of undocumented process-parameter bits.

## Patch Boundary

Keep the compatibility workaround, but make it temporary and mask-scoped:

- save the original `WindowFlags`
- clear only `0x5000` while calling the real Shell API
- restore only those saved `0x5000` bits after the call
- preserve any other `WindowFlags` changes the real API makes during the call

This does not prove the crash root cause is fixed. It removes permanent
process-parameter mutation while keeping the existing crash workaround.

## Acceptance Gate

- No permanent `ProcessParms->WindowFlags &= ~0x5000` mutation remains.
- The real Shell API is still called with the local workaround active.
- The saved `0x5000` bits are restored after the call.
- Runtime gate remains open: process-level AppUserModelID still works, the
  WindowTitle crash does not return, and later process-parameter reads observe
  the original `0x5000` bits.
