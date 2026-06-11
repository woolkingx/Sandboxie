---
kind: srev-ledger-entry
id: SREV-250
title: Win32k Electron Comment Boundary
status: patched-comment-topology-after-srev-087-runtime-matrix-review-no-behavior-change
owner: Sandboxie/core/dll/Win32.c and Sandboxie/core/dll/proc.c
spec: docs/plan/srev-250-win32k-electron-comment-boundary.md
schema: docs/plan/srev-250-win32k-electron-comment-boundary.schema.json
checker: docs/plan/check-srev-250.py
runtime_gate: Inherited from SREV-087 Electron and Chromium GPU-process Windows runtime matrix
---

### SREV-250: Win32k Electron Comment Boundary

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | patched comment/topology after SREV-087 runtime-matrix review; no behavior change |
| Evidence | SREV-087 already established that `Win32_Init` must not toggle Electron GPU product behavior from the mere fact that win32k syscall hooks are being installed. The old `Win32.c` source comment still said to disable the Electron path when the required win32k syscalls are hooked, and carried two commented-out lines for the inactive flag assignment. The adjacent inactive `proc.c` command-line path still used anonymous workaround/hack wording around the same Electron GPU product-policy boundary. |
| Data | `Win32_Init`, `SBIE_FLAG_WIN32K_HOOKABLE`, `EnableWin32kHooks`, `UseWin32kHooks`, `Win32_HookWin32SysCalls`, `Win32_HookWin32WoW64`, `Proc_CreateProcessInternalW`, `Proc_IsLikelyElectronProcess`, `SbieApi_LogMsgExt` 2189, Electron/Chromium GPU behavior, inactive `Dll_ElectronWorkaround`, and SREV-087 runtime matrix. |
| Schema | `WIN32K_ELECTRON_COMMENT_BOUNDARY` says win32k hook installation is local Sandboxie runtime state rather than proof of Electron GPU compatibility; Electron GPU command-line handling remains inactive until Windows runtime matrix evidence proves replacement coverage; `proc.c` Electron GPU command-line comments must name SREV-250 and stay comment-only; `Win32_Init` must not assign `Dll_ElectronWorkaround`; comment-only clarification must not change win32k hook gates, hook calls, Electron detection, or process creation behavior; SREV-087 remains the behavior owner for the runtime matrix. |
| Topology | `process flags + settings -> Win32_Init win32k hook decision -> syscall wrapper patching -> no Electron GPU policy mutation`; `Proc_CreateProcessInternalW -> likely Electron child-process observation -> inactive Dll_ElectronWorkaround command-line mutation remains commented -> no command-line mutation without runtime matrix proof`. Runtime proof remains `Electron / Chromium GPU process -> EnableWin32kHooks / UseWin32kHooks matrix -> HVCI on/off, WOW64/native, hardware/software rendering -> only then decide product behavior`. |
| Logic Risk | The old `Win32.c` comment implied a direct edge from "required syscalls are hooked" to "Electron product path can be disabled." The old `proc.c` comments framed the inactive command-line path as anonymous compatibility residue. Microsoft exposes process mitigation state and WDDM/DDI topology, but does not expose a stable public "complete Electron GPU win32k hook set" contract. Local source also shows the Electron command-line path is already inactive in `proc.c`. |
| Official Shape | `docs/plan/srev-250-win32k-electron-comment-boundary.md` inherits SREV-087 Microsoft `ProcessSystemCallDisablePolicy` and WDDM references. `docs/plan/srev-250-win32k-electron-comment-boundary.schema.json` records the JSON Schema draft-07 local `WIN32K_ELECTRON_COMMENT_BOUNDARY` contract. |
| Fix | Comment-only source clarification. `Win32.c` now says Electron GPU command-line handling stays inactive until a Windows runtime matrix proves win32k syscall hook coverage. The inactive commented-out flag declaration and assignment were removed from `Win32_Init`. `proc.c` now labels the inactive Electron GPU command-line path as SREV-250-owned comment-only topology. No process creation condition, logging call, command-line allocation, or command-line mutation changed. |
| Acceptance Gate | `docs/plan/check-srev-250.py` validates the draft-07 schema, inherited official references, SREV-087 adjacency, the new `Win32.c` comment, absence of active or commented `Dll_ElectronWorkaround = FALSE` mutation in `Win32_Init`, unchanged win32k hook gates and hook calls, `proc.c` SREV-250 comment wording, inactive Electron command-line path preservation, and the ledger fragment; `docs/plan/check-srev-250.sh` is the targeted wrapper. Runtime gate is inherited from SREV-087: Electron and Chromium GPU-process launches still need the Windows runtime matrix before any behavior change. |
