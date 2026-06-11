# SREV-250: Win32k Electron Comment Boundary

## Stage Gate

| Field | Value |
|---|---|
| Stage | schema -> topology -> logic -> action -> verify |
| Input artifact | `Sandboxie/core/dll/Win32.c`, `Sandboxie/core/dll/proc.c`, SREV-087, Microsoft process-mitigation and WDDM references |
| Output artifact | `docs/plan/srev-250-win32k-electron-comment-boundary.schema.json`, `docs/plan/check-srev-250.py`, `docs/plan/check-srev-250.sh`, ledger fragment, comment-only source clarification |
| Owner | `Win32_Init` win32k hook enablement plus `proc.c` inactive Electron GPU command-line comments |
| Acceptance gate | targeted source checker plus SREV-087 compatibility checker, core coverage, and diff checkpoint |

## Evidence

SREV-087 already established that `Win32_Init` must not toggle Electron GPU
product behavior from the mere fact that win32k syscall hooks are being
installed. The old `Win32.c` source comment still said to disable the Electron
path when the required win32k syscalls are hooked, and carried two commented-out
lines for the inactive flag assignment. The adjacent inactive `proc.c` command
line path still used anonymous workaround/hack wording around the same Electron
GPU product-policy boundary.

The current legal topology is:

```text
Win32_Init
  -> EnableWin32kHooks / UseWin32kHooks
  -> Win32_HookWin32SysCalls or Win32_HookWin32WoW64
  -> no Electron product-policy toggle
```

The Electron/Chromium compatibility topology remains separate:

```text
Dll_TryDetectElectron / Ldr_DetectImageType
  -> Chrome-like classification
  -> proc.c logs likely Electron child launches
  -> inactive GPU command-line fallback remains commented out
  -> runtime matrix must prove GPU behavior before policy changes
```

Official references are inherited from SREV-087:

- https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-process_mitigation_system_call_disable_policy
- https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-getprocessmitigationpolicy
- https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-setprocessmitigationpolicy
- https://learn.microsoft.com/en-us/windows-hardware/drivers/display/windows-vista-and-later-display-driver-model-operation-flow
- https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/_display/

## Data

`Win32_Init`, `SBIE_FLAG_WIN32K_HOOKABLE`, `EnableWin32kHooks`,
`UseWin32kHooks`, `Win32_HookWin32SysCalls`, `Win32_HookWin32WoW64`,
`Proc_CreateProcessInternalW`, `Proc_IsLikelyElectronProcess`, `SbieApi_LogMsgExt`
2189, Electron/Chromium GPU behavior, inactive `Dll_ElectronWorkaround`, and
SREV-087 runtime matrix.

## Schema

`WIN32K_ELECTRON_COMMENT_BOUNDARY` says:

- win32k hook installation is local Sandboxie runtime state, not proof of
  Electron GPU compatibility;
- Electron GPU command-line handling remains inactive until Windows runtime
  matrix evidence proves replacement coverage;
- `proc.c` Electron GPU command-line comments must name SREV-250 and stay
  comment-only;
- `Win32_Init` must not assign `Dll_ElectronWorkaround`;
- comment-only clarification must not change win32k hook gates, hook calls,
  Electron detection, or process creation behavior;
- SREV-087 remains the behavior owner for the runtime matrix.

## Topology

```text
process flags + settings
  -> Win32_Init win32k hook decision
  -> syscall wrapper patching
  -> no Electron GPU policy mutation

Proc_CreateProcessInternalW
  -> likely Electron child-process observation
  -> inactive Dll_ElectronWorkaround command-line mutation remains commented
  -> no command-line mutation without runtime matrix proof
```

The runtime proof topology remains:

```text
Electron / Chromium GPU process
  -> EnableWin32kHooks / UseWin32kHooks matrix
  -> HVCI on/off, WOW64/native, hardware/software rendering
  -> only then decide product behavior
```

## Logic Risk

The old comment implied a direct edge from "required syscalls are hooked" to
"Electron product path can be disabled." Microsoft exposes process mitigation
state and WDDM/DDI topology, but does not expose a stable public "complete
Electron GPU win32k hook set" contract. Local source also shows the Electron
command-line path is already inactive in `proc.c`.

The legal fix is to remove the stale boolean-toggle hint from `Win32.c`, replace
anonymous `proc.c` compatibility comments with SREV-250 ownership wording, and
leave the runtime-matrix gate explicit.

## Fix

Comment-only source clarification. `Win32.c` now says Electron GPU
command-line handling stays inactive until a Windows runtime matrix proves
win32k syscall hook coverage. The inactive commented-out flag declaration and
assignment were removed from `Win32_Init`. `proc.c` now labels the inactive
Electron GPU command-line path as SREV-250-owned comment-only topology. No
process creation condition, logging call, command-line allocation, or
command-line mutation changed.

## Acceptance Gate

`docs/plan/check-srev-250.py` validates the draft-07 schema, inherited official
references, SREV-087 adjacency, the new `Win32.c` comment, absence of active or
commented `Dll_ElectronWorkaround = FALSE` mutation in `Win32_Init`, unchanged
win32k hook gates and hook calls, `proc.c` SREV-250 comment wording, inactive
Electron command-line path preservation, and the ledger fragment.

Runtime gate: inherited from SREV-087. Electron and Chromium GPU-process
launches still need the Windows runtime matrix before any behavior change.
