---
kind: srev-ledger-entry
id: SREV-087
title: Win32k Electron Workaround Boundary
status: source-level-classified-after-official-win32k-mitigation-policy-and-wddm-graphic
owner: Sandboxie/core/dll/Win32.c
spec: docs/plan/srev-087-win32k-electron-workaround-boundary.md
schema: docs/plan/srev-087-win32k-electron-workaround-boundary.schema.json
checker: docs/plan/check-srev-087.py
runtime_gate: "Electron and Chromium GPU-process launches must be tested across `EnableWin32kHooks` / `UseWin32kHooks`, HVCI on/off, WOW64/native, Chrome-like DLL detection, and hardware/software rendering fallback"
---
### SREV-087: Win32k Electron Workaround Boundary

| Field | Content |
|---|---|
| Severity | [major] |
| Status | source-level classified after official Win32k mitigation-policy and WDDM graphics-flow shape; no source patch because Windows Electron GPU runtime matrix is still required |
| Evidence | `Sandboxie/core/dll/Win32.c` previously contained a comment saying the Electron workaround could be disabled when the required win32k syscalls were hooked. Microsoft documents `ProcessSystemCallDisablePolicy` / `PROCESS_MITIGATION_SYSTEM_CALL_DISABLE_POLICY` as the public boundary for blocking NTUser/GDI system calls, and documents WDDM rendering as Direct3D runtime -> user-mode display driver -> kernel-mode display miniport / Dxgkrnl flow. Local source shows `Dll_ElectronWorkaround` and the Electron GPU command-line mutation are already inactive in `Sandboxie/core/dll/proc.c`, while Electron/Chromium detection flows through `Sandboxie/core/dll/dllmain.c` and `Sandboxie/core/dll/ldr.c` into Chrome-like handling and `UseWin32kHooks`. |
| Data | `SBIE_FLAG_WIN32K_HOOKABLE`, `EnableWin32kHooks`, per-image `UseWin32kHooks`, Chrome default GPU acceleration hook policy, Electron/Chromium detection, inactive Electron command-line workaround, process mitigation query, and WDDM graphics runtime path. |
| Schema | `WIN32K_ELECTRON_WORKAROUND_BOUNDARY` says Win32k syscall hookability is local Sandboxie runtime state, not a Microsoft public API guarantee; `ProcessSystemCallDisablePolicy` is the public mitigation boundary for blocking NTUser/GDI system calls; WDDM graphics work flows through Direct3D runtime, UMD, KMD, and Dxgkrnl; Electron workaround state must not be toggled from a hook-installed boolean alone; the inactive Electron command-line workaround remains inactive until a Windows runtime matrix proves replacement coverage; this SREV does not extend win32u syscall patching or revive Electron command-line mutation. |
| Topology | Driver syscall table initialization produces `Syscall_MaxIndex32`; process API projects `SBIE_FLAG_WIN32K_HOOKABLE`; `Win32_Init` combines that with `EnableWin32kHooks` and `UseWin32kHooks` before patching win32u syscall wrappers. Electron detection separately classifies arbitrary Electron apps as Chrome-like through `Dll_TryDetectElectron` / `Ldr_DetectImageType`; the old GPU command-line workaround remains commented out. |
| Logic Risk | Treating "hook installed" as equivalent to "Electron GPU compatibility covered" would connect an internal syscall-patching implementation detail to a product compatibility policy that Microsoft does not expose as a stable public contract. The correct next evidence is Windows runtime capture of Electron/Chromium GPU-process behavior, not a direct code toggle. |
| Official Shape | `docs/plan/srev-087-win32k-electron-workaround-boundary.md` records Microsoft `PROCESS_MITIGATION_SYSTEM_CALL_DISABLE_POLICY`, `GetProcessMitigationPolicy`, `SetProcessMitigationPolicy`, WDDM operation flow, and Display/Graphics DDI references. `docs/plan/srev-087-win32k-electron-workaround-boundary.schema.json` records the JSON Schema draft-07 local `WIN32K_ELECTRON_WORKAROUND_BOUNDARY` contract. |
| Fix | No behavior patch in this SREV. The current source keeps the Electron command-line path inactive and leaves win32k hook enablement under `EnableWin32kHooks` and per-image `UseWin32kHooks`; SREV-250 later clarifies the source comment so this remains a runtime-matrix decision rather than a boolean hook-installation decision. |
| Acceptance Gate | `docs/plan/check-srev-087.py` validates the draft-07 schema, official mitigation and WDDM references, local win32k hookability topology, Electron detection / inactive workaround evidence, absence of an active `Dll_ElectronWorkaround` toggle from `Win32_Init`, and ledger entry; `docs/plan/check-srev-087.sh` is the matrix wrapper. Windows gate: Electron and Chromium GPU-process launches must be tested across `EnableWin32kHooks` / `UseWin32kHooks`, HVCI on/off, WOW64/native, Chrome-like DLL detection, and hardware/software rendering fallback. |
