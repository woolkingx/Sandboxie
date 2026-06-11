# SREV-087: Win32k Electron Workaround Boundary

## Data

`Sandboxie/core/dll/Win32.c` owns DLL-side win32u/win32k syscall hook
installation. The comment-admitted data shape in this file is:

```text
Win32k hookability process flag
EnableWin32kHooks global setting
UseWin32kHooks image setting
Chrome default GPU acceleration syscall hook policy
Electron detection / compatibility state
inactive Electron command-line workaround
win32u syscall patching boundary
```

## Official Shape

Microsoft documents `PROCESS_MITIGATION_SYSTEM_CALL_DISABLE_POLICY` as imposing
restrictions on process system calls. Its `DisallowWin32kSystemCalls` bit means
the process is not permitted to perform GUI system calls.

Microsoft documents `GetProcessMitigationPolicy` and `SetProcessMitigationPolicy`
as the public process-mitigation policy boundary. For
`ProcessSystemCallDisablePolicy`, the buffer shape is
`PROCESS_MITIGATION_SYSTEM_CALL_DISABLE_POLICY`; Microsoft describes this policy
as disabling NTUser/GDI functions at the lowest layer.

Microsoft documents WDDM rendering as a public Direct3D runtime -> user-mode
display driver -> kernel-mode display miniport flow. The graphics/display DDI
surface is documented through WDK headers such as `d3dkmthk.h`, `d3dumddi.h`,
`d3dkmddi.h`, and `dxgiddi.h`.

Microsoft does not document a stable public contract for Sandboxie to decide
that arbitrary `win32u.dll` `NtUser*` / `GdiDdDDI*` syscall patching is complete
enough to replace a product-level Electron compatibility policy.

```text
https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-process_mitigation_system_call_disable_policy
https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-getprocessmitigationpolicy
https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-setprocessmitigationpolicy
https://learn.microsoft.com/en-us/windows-hardware/drivers/display/windows-vista-and-later-display-driver-model-operation-flow
https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/_display/
```

## Schema

Local schema:

```text
docs/plan/srev-087-win32k-electron-workaround-boundary.schema.json
```

The boundary contract is:

```text
Win32k syscall hookability is local Sandboxie runtime state, not a Microsoft public API guarantee
ProcessSystemCallDisablePolicy is the public mitigation boundary for blocking NTUser/GDI system calls
WDDM graphics work flows through Direct3D runtime, UMD, KMD, and Dxgkrnl
Electron workaround state must not be toggled from a hook-installed boolean alone
the inactive Electron command-line workaround remains inactive until a Windows runtime matrix proves replacement coverage
this SREV does not extend win32u syscall patching or revive Electron command-line mutation
```

## Topology

```text
driver Syscall_Init_List32 / Syscall_Init_Table32
  -> Syscall_MaxIndex32
  -> process API SBIE_FLAG_WIN32K_HOOKABLE
  -> dll Win32_Init
  -> EnableWin32kHooks + UseWin32kHooks
  -> Win32_HookWin32SysCalls / Win32_HookWin32WoW64
```

Electron compatibility has a separate detection path:

```text
Dll_TryDetectElectron / Ldr_DetectImageType
  -> DLL_IMAGE_GOOGLE_CHROME treatment
  -> Chrome default UseWin32kHooks
  -> inactive Proc_CreateProcessInternalW Electron GPU command-line workaround
```

The public Windows boundary around GUI syscall blocking is:

```text
GetProcessMitigationPolicy / SetProcessMitigationPolicy
  -> ProcessSystemCallDisablePolicy
  -> PROCESS_MITIGATION_SYSTEM_CALL_DISABLE_POLICY
```

The public graphics boundary is:

```text
Direct3D runtime
  -> user-mode display driver
  -> Dxgkrnl / kernel-mode display miniport
  -> hardware queue / present
```

## Logic Risk

The old comment in `Win32.c` said to disable the Electron workaround once the
required win32k syscalls were hooked. That sounded like a simple boolean edge,
but the official API shape does not define a "complete Electron GPU win32k hook
set" that Sandboxie can infer from `Win32_HookWin32SysCalls` succeeding.

Local evidence also shows the named Electron command-line workaround is already
inactive: `Dll_ElectronWorkaround` and the GPU-process command-line mutation are
commented out in `proc.c`. Current Electron handling is detection/classification
as Chrome-like, plus the `UseWin32kHooks` policy path.

Therefore the safe SREV action is classification, not a source patch. Reviving
or disabling the Electron workaround from `Win32_Init` would be shape-first
wrong: it would connect an internal hook-installation state to product
compatibility policy without a Windows runtime matrix proving which
`NtUser*` / `GdiDdDDI*` calls Electron/Chromium GPU processes actually need
under Sandboxie token and desktop constraints.

## Fix

No behavior patch in this SREV. The current source keeps the Electron
command-line path inactive and leaves win32k hook enablement under
`EnableWin32kHooks` and per-image `UseWin32kHooks`. SREV-250 later clarifies
the source comment so this remains a runtime-matrix decision rather than a
boolean hook-installation decision.

## Acceptance Gate

`docs/plan/check-srev-087.py` validates the draft-07 schema, official mitigation
and WDDM references, local win32k hookability topology, Electron detection /
inactive workaround evidence, absence of an active `Dll_ElectronWorkaround`
toggle from `Win32_Init`, and ledger entry.

Windows gate: Electron and Chromium GPU-process launches must be tested across
`EnableWin32kHooks` / `UseWin32kHooks`, HVCI on/off, WOW64/native, Chrome-like
DLL detection, and hardware/software rendering fallback. Source-level gates do
not prove this runtime matrix.
