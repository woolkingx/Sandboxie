# SREV-106: Low Inject ARM64EC Syscall Entrypoint

## Data

`Sandboxie/core/low/inject.c` owns the low-level injection detour that loads
`SbieDll.dll` into the target process before normal execution continues. The
uncovered comment-risk line was in `InitInject`, where the injected bootstrap
chooses function pointers for `NtProtectVirtualMemory`, `NtRaiseHardError`, and
`NtDeviceIoControlFile`.

The data shape is split by process architecture:

```text
WOW64 target
  -> find 32-bit ntdll exports from ntdll_wow64_base
  -> store 32-bit Nt* export pointers in INJECT_DATA

native / ARM64EC target
  -> use SBIELOW_DATA pre-captured native/EC entrypoints
  -> store those entrypoints in INJECT_DATA
```

## Official Shape

Microsoft documents Arm64EC as an ABI that lets x64 and Arm64EC code
interoperate in one process on Windows on Arm. Microsoft documents Arm64EC call
checkers, exit thunks, and fast-forward sequences as part of that ABI.

Microsoft also documents `__declspec(hybrid_patchable)` as generating a
fast-forward sequence: a small x64 function that transfers execution to the real
Arm64EC function. That official shape matches Sandboxie's local
`Hook_GetFFSTarget` helper for ordinary hybrid exports.

Microsoft documents native system services as `Nt` / `Zw` routines: user-mode
applications reach them through system calls, and kernel-mode callers can call
the routines directly. Sandboxie's low-level path is user-mode bootstrap code,
so the local owner must preserve its own captured syscall-wrapper entrypoints
instead of treating syscall exports as ordinary FFS-only functions.

```text
https://learn.microsoft.com/en-us/windows/arm/arm64ec
https://learn.microsoft.com/en-us/windows/arm/arm64ec-abi
https://learn.microsoft.com/en-us/cpp/cpp/hybrid-patchable?view=msvc-170
https://learn.microsoft.com/en-us/windows-hardware/drivers/kernel/using-nt-and-zw-versions-of-the-native-system-services-routines
https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/_kernel/
```

## Schema

Local schema:

```text
docs/plan/srev-106-low-inject-arm64ec-syscall-entrypoint.schema.json
```

The ARM64EC injection entrypoint contract is:

```text
ordinary ARM64EC exports may be FFS-resolved to native EC targets
Nt* syscall exports are routed through SbieLow syscall-wrapper state
WOW64 injection uses 32-bit ntdll export pointers
native / ARM64EC injection uses pre-captured native or EC entrypoints
NtDeviceIoControlFile may point to the EC wrapper installed by PrepSyscalls
the injection detour must keep using INJECT_DATA entrypoints while restoring the hook and loading SbieDll
```

## Topology

Source topology after this SREV:

```text
lowlevel_inject.c
  -> captures ntdll base, native Nt* entrypoints, and syscall data
  -> for ARM64EC, appends EC syscall wrapper data and EcExitThunkPtr
  -> writes SBIELOW_DATA into the target process

core/low/init.c
  -> PrepSyscalls installs SbieLow syscall wrapper state
  -> ARM64EC may point data->NtDeviceIoControlFile at NtDeviceIoControlFileEC

core/low/inject.c
  -> WOW64 branch resolves 32-bit ntdll exports
  -> native / ARM64EC branch uses SBIELOW_DATA native/EC entrypoints
  -> DetourFunc restores the hook and calls LdrLoadDll / SbieDll ordinal 1
```

`Hook_GetFFSTarget` remains the ordinary-export helper used by ARM64EC hooking
paths. It is not promoted to the owner of Nt* syscall entrypoint selection in
`InitInject`.

## Logic Risk

The old comment correctly resisted FFS-resolving syscall exports, but it framed
the reason as a vague failure. That invites the wrong repair: retry FFS parsing
for Nt* exports or treat syscall wrappers like ordinary hybrid functions.

The correct local rule is topology-shaped. Ordinary hybrid exports can be
resolved through FFS. Syscall exports belong to the SbieLow syscall-wrapper
state already prepared from driver/runtime data, so injection-time calls use
the pre-captured native/EC entrypoints.

## Fix

Comment-only source clarification. The stale "does not work for syscalls"
comment now states that ordinary ARM64EC exports can be FFS-resolved, while
Nt* syscall exports are routed through SbieLow syscall-wrapper state and must
keep the pre-captured native/EC entrypoints for injection-time calls.

No pointer assignment, FFS parsing, syscall wrapper construction, hook target,
detour patch size, DLL load, or error-reporting behavior changed.

## Acceptance Gate

`docs/plan/check-srev-106.py` validates the draft-07 schema, official
references, WOW64 export path, native / ARM64EC pre-captured entrypoint path,
local EC syscall-wrapper preparation, FFS helper boundary, stale "does not work"
wording removal, and ledger entry. `docs/plan/check-srev-106.sh` is the matrix
wrapper.

Runtime gate: Windows on Arm matrix with ARM64EC target process, x64-emulated
target process, WOW64 target process where applicable, `NtProtectVirtualMemory`
hook restore, `NtRaiseHardError` injection failure path, `NtDeviceIoControlFile`
driver call path, FFS-resolved ordinary exports, SbieLow syscall hook enabled
and disabled, and Driver Verifier / loader-lock observation during early
process initialization.
