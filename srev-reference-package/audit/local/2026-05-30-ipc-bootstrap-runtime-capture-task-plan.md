# IPC Bootstrap Runtime Capture Task Plan

Goal: capture the Sandboxie startup failure that logs `SBIE2308 [77 / C0000022]`
and `SBIE2310` during box startup, without treating a larger name buffer or an
INI compatibility switch as a fix.

Architecture: this is a local runtime-capture patch only. The Linux worktree is
the source owner. The Windows VM receives the instrumented DLL source, builds a
test `SbieDll.dll`, and emits SbieSvc event-log evidence. The resulting evidence
decides whether the real owner is `Ipc_CreateObjects`, the driver
`Ipc_Api_CreateDirOrLink` boxed-path gate, or a name-buffer push/pop imbalance.

## Evidence

- Runtime after reboot: `SbieSvc` and `SbieDrv` start cleanly.
- First sandboxed `notepad.exe` launch logs `SBIE2308 Could not create object
  directory: [77 / C0000022]`, followed by `SBIE2310 Name buffer is approaching
  overflow`.
- Second sandboxed launch repeats the same `2308/2310` pair.
- `DisableBoxedWinSxS=y` does not remove the `2308/2310` pair, so the SXS
  route is not the root owner for this symptom.
- Instrumented runtime log proved `err=77 status=C0000022 step=76` in
  `Ipc_CreateObjects` before symbolic-link creation:
  `obj=\Sandbox\vboxuser\New_Box\BNOLINKS`,
  `copy=\Sandbox\vboxuser\New_Box\Session_0\BaseNamedObjects`, and
  `bnolinks=\Sandbox\vboxuser\New_Box\BNOLINKS`.
- `SbieDll_GetHandlePath` is the caller reaching the existing `SBIE2310`
  name-buffer threshold in `Start.exe`; that is downstream of the IPC bootstrap
  access-denied failure, not the root owner for `err=77`.
- SREV-037 driver-side `Box_IsBoxedPath(proc->box, ipc, ...)` accepts paths
  under the configured IPC root, whose default is
  `\Sandbox\%USER%\%SANDBOX%\Session_%SESSION%`. The current `BNOLINKS`
  construction creates a sibling at `\Sandbox\%USER%\%SANDBOX%\BNOLINKS`, so the
  driver correctly rejects it with `STATUS_ACCESS_DENIED`.

## Hypotheses

H1: `Ipc_CreateObjects` constructs a `BNOLINKS` object directory or symbolic-link
target that fails the driver `Box_IsBoxedPath(..., ipc, ...)` gate with
`STATUS_ACCESS_DENIED`.

H2: `Ipc_GetName` or an object-name hook re-enters a name-resolution path before
the TLS name-buffer stack is popped, so the `2308` object-directory failure is
only the visible downstream error.

## Task Plan

- [x] Step 1: Instrument `Ipc_CreateObjects` to log the failing step, object
  name, target name, `CopyPath`, `TruePath`, and `BNOLINKS` when `errlvl` is
  set.
- [x] Step 2: Enable `NAME_BUFFER_DEBUG` and emit local `LTEST` messages with
  the TLS name-buffer operation, function name, depth, and image name whenever
  the existing `SBIE2310` threshold is reached.
- [x] Step 3: Build x64 Release `SandboxDll.sln` on the Windows VM and replace
  only the portable test `SbieDll.dll` after backing it up.
- [x] Step 4: Reproduce `Start.exe /box:New_Box C:\Windows\System32\notepad.exe`
  twice and collect SbieSvc event logs.
- [x] Step 5: Remove or isolate the instrumentation before any upstream-facing
  commit or PR.
- [x] Step 6: Move the `BNOLINKS` directory under `Dll_BoxIpcPath`, preserve the
  existing session link topology, rebuild, and verify that startup no longer
  logs `SBIE2308 [77 / C0000022]` for `New_Box`.

## Runtime Result After Step 6

- Rebuilt x64 Release `SbieDll.dll` and deployed it to
  `C:\temp\Sandboxie-Plus\SbieDll.dll`.
- New deployed DLL SHA-256:
  `D3D7EEEE74C5943F3C10527CA889EC7FDE3D1FB3922DEA01651B97334598ECB5`.
- Repeated `Start.exe /box:New_Box C:\Windows\System32\notepad.exe`,
  terminated the box, and launched it again.
- Result: `SBIE2308 [77 / C0000022]`, `SBIE2203`, and `SBIE2204` no longer
  appeared in `SbieSvc` event logs for the test window.
- After disabling `NAME_BUFFER_DEBUG`, remaining `SBIE2310` entries still appear
  from `Start.exe` without local `LTEST name-buffer` records. They are a
  separate baseline warning from the name-buffer stack and are no longer tied to
  the `SBIE2308 [77 / C0000022]` IPC bootstrap failure chain.

## Follow-Up Hypothesis

H3: Moving `BNOLINKS` under `Dll_BoxIpcPath` satisfies the SREV-037 boxed-path
gate but changes the object-link topology enough to create recursive name
resolution in `Start.exe`, which then reaches the name-buffer depth guard and
exits with `SBIE2310` before launching target programs.

Condition C: `BNOLINKS` is constructed as
`\Sandbox\%USER%\%SANDBOX%\Session_%SESSION%\BNOLINKS` and `Start.exe /box`
runs any target program.

Predicted E: `SBIE2308 [77 / C0000022]` disappears, but every `Start.exe /box`
launch exits quickly with `rc=-1` and `SBIE2310`; no target process starts.

Observed E: ITM-003 and simple notepad launches match this prediction.

Next action: restore the original DLL-side box-level `BNOLINKS` topology, then
make the driver-side SREV-037 gate accept only this narrow bootstrap auxiliary
directory while keeping normal IPC object and symbolic-link targets boxed under
the configured IPC root.

Acceptance gate: the next failure log must identify whether `errlvl=77` failed
on the BNOLINKS directory or BNOLINKS symbolic-link creation, and must include
the name-buffer function that first reaches depth/count threshold.

## Runtime Result After Driver BNOLINKS Exception

- Rebuilt and deployed `SbieDrv.sys` with the SREV-037 same-box `BNOLINKS`
  auxiliary subtree exception.
- Rebuilt and deployed `SbieDll.dll` with `BNOLINKS` restored to its original
  box-level topology.
- Result: `SBIE2308 [77 / C0000022]`, `SBIE2203`, and the original
  `SBIE2204 RpcSs/DcomLaunch` startup chain no longer appeared for the IPC
  bootstrap path.
- Remaining failure: `Start.exe` still exited before launching targets because
  `SbieDll_GetHandlePath` recursively reached the TLS name-buffer guard.
- Debug evidence with `NAME_BUFFER_DEBUG` showed the first high-depth pushes
  were all `SbieDll_GetHandlePath` in `Start.exe`; return-address/PDB
  symbolization mapped the call site to
  `File_NtQueryVolumeInformationFile` in `Sandboxie/core/dll/file_dir.c`.

## Follow-Up Runtime Result: SREV-279 Volume Reentrancy Gate

- SREV-279 now owns a narrow `File_NtQueryVolumeInformationFile` reentrancy
  gate: `ipc_KnownDlls_lock` and `file_NtQueryVolumeInformation_lock` route
  nested volume-info calls directly to `__sys_NtQueryVolumeInformationFile`
  instead of recursively calling `SbieDll_GetHandlePath`.
- The local debug probes were removed from source before the clean runtime
  smoke: `NAME_BUFFER_DEBUG` remains disabled and `Ipc_CreateObjects` now logs
  only the existing `SBIE2308` failure code on `errlvl`.
- Clean x64 Release `SbieDll.dll` was rebuilt on the Windows VM and deployed to
  `C:\temp\Sandboxie-Plus\SbieDll.dll`; deployed SHA-256:
  `A9A3EF5F3B024E2E73CA1DA9186E1B3B7F1C302F0453A0E06AA3B31B7908084A`.
- Runtime proof on the Windows VM:
  `Start.exe /box:New_Box /wait C:\Windows\System32\cmd.exe /c exit 0` run
  through Task Scheduler as `vboxuser` returned `SMOKE_RC=0`.
- Clean scheduled-task smoke at `2026-05-30 08:25:12 +08:00` returned
  `TERM_RC=0` and `SMOKE_RC=0`; `SbieDrv` and `SbieSvc` remained running after
  the run.
- Evidence after the gate: no Sandboxie/SBIE Windows Application event was
  emitted in the smoke window, and the earlier local `LTEST` probes are no
  longer present in the deployed source path.
- New independent issue: launching from non-interactive SSH still returns
  quickly and Sandboxie logs `SBIE2204 Cannot start sandboxed service RpcSs
  (1008)` / `SBIE2337 [33 / 1008]`. The scheduled task path proves this is no
  longer the same `SbieDll_GetHandlePath` name-buffer recursion.
