# Issue-Driven Software Compatibility Test Matrix

Goal: validate the local Sandboxie build against upstream GitHub issues that
name real software, versions, sandbox type, and observable symptoms. Each case
must reproduce or fail to reproduce before any code change is considered.

Architecture: GitHub issues provide the repro claim; local md/specs provide the
owner and boundary rules; the Windows VM provides runtime evidence. Source
changes are only legal after a case has a falsifiable hypothesis and captured
evidence showing the owner path.

## Rules

- Read this matrix and the target SREV/KPATH md before changing source.
- Do not treat local instrumentation messages as upstream symptoms.
- Disable or isolate `NAME_BUFFER_DEBUG` before compatibility testing.
- Test one issue at a time in a clean box state.
- Record exact software version, download URL, sandbox type, command, elapsed
  time, process state, Sandboxie event logs, and Windows event logs.
- If a workaround INI key is tested, record it as a separate run, not as a fix.
- No code patch without: `H`, `Condition C`, `Predicted E`, actual evidence,
  owner boundary, and verification gate.

## Candidate Issues

| ID | Upstream Issue | Software / Repro | Sandbox Type | Primary Symptom | Priority | Testability |
|---|---|---|---|---|---|---|
| ITM-001 | `#3204` `https://github.com/sandboxie-plus/Sandboxie/issues/3204` | `npp.8.5.5.Installer.x64.exe` from Notepad++ release | Green / Application Compartment / `NoSecurityIsolation=y` | Installer crashes when clicking Finish; Notepad++ is not launched | P0 | Direct download, scriptable install start, GUI finish may need desktop/RDP or silent-flag probe |
| ITM-002 | `#2849` `https://github.com/sandboxie-plus/Sandboxie/issues/2849` | Many installers; original private/archival game installer, later MSI | Green / Application Compartment | Installer/explorer slow start or hang for around 3 minutes; yellow box works | P1 | Needs public substitute installer or reporter-provided sample; use ITM-001 as first public representative |
| ITM-003 | `#4356` `https://github.com/sandboxie-plus/Sandboxie/issues/4356` | 32-bit `PrintDlgW` repro program | Green / Application Compartment / WoW64 | `PrintDlgW` hangs around one minute due SplWow64 RPC endpoint mismatch | P1 | Fully scriptable by compiling a small 32-bit program on VM |
| ITM-004 | `#1931` `https://github.com/sandboxie-plus/Sandboxie/issues/1931` | `sc.exe query` | Yellow / Standard isolation | SCM query hangs or times out; maintainer notes `ntsvcs` endpoint trade-off | P2 | Command-only repro, but belongs to SCM/service broker design, not installer path |

## Current Baseline

- Windows VM: `192.168.213.80`, portable Sandboxie path
  `C:\temp\Sandboxie-Plus`.
- Local SREV-037/SREV-299 IPC bootstrap fix is deployed in `SbieDrv.sys`; the
  driver accepts only the same-box `BNOLINKS` bootstrap auxiliary subtree in
  addition to the configured boxed IPC root.
- Local SREV-279 volume-info reentrancy fix is deployed in `SbieDll.dll` hash
  `A9A3EF5F3B024E2E73CA1DA9186E1B3B7F1C302F0453A0E06AA3B31B7908084A`.
- Runtime proof after the SREV-037/SREV-279/SREV-299 chain: scheduled
  `Start.exe /box:New_Box /wait C:\Windows\System32\cmd.exe /c exit 0` as
  `vboxuser` returned `TERM_RC=0` and `SMOKE_RC=0` at
  `2026-05-30 08:25:12 +08:00`; `SbieDrv` and `SbieSvc` remained running.
- `NAME_BUFFER_DEBUG` has been disabled and local `LTEST` source probes were
  removed before compatibility testing. Non-interactive SSH launch still shows
  a separate `RpcSs (1008)` / `SBIE2337 [33 / 1008]` path, so issue-driven GUI
  or scheduled-task repros must not use SSH session behavior as the sole owner.

## ITM-001: Notepad++ Installer 8.5.5

Source issue: `https://github.com/sandboxie-plus/Sandboxie/issues/3204`

Repro claim:

```text
Create a new Application Compartment (NO Isolation) box with default settings.
Run npp.8.5.5.Installer.x64.exe inside the box.
Install succeeds until Finish; clicking Finish crashes the installer and
Notepad++ is not launched.
```

Download:

```text
https://github.com/notepad-plus-plus/notepad-plus-plus/releases/download/v8.5.5/npp.8.5.5.Installer.x64.exe
```

Hypothesis slot:

```text
H:
Condition C:
Predicted E:
Actual:
Owner:
Next action:
```

Test runs:

| Run | Build | Box Config | Action | Expected | Actual | Evidence |
|---|---|---|---|---|---|---|
| ITM-001-A | local SREV-037/SREV-279/SREV-299 build, instrumentation disabled | `New_Box`, `NoSecurityIsolation=y` | Launch installer, complete install, click Finish | No crash; Notepad++ launches or installer exits cleanly | pending | pending |

Current artifact status:

- GitHub issue URL for `npp.8.5.5.Installer.x64.exe` now returns `404`.
- GitHub release API for `notepad-plus-plus/notepad-plus-plus` tag `v8.5.5`
  currently reports no binary assets.
- The official Notepad++ `v8.5.5` download page currently links binary downloads
  forward to `v8.5.6` and only leaves checksum assets for `v8.5.5` on GitHub.
- Do not replace this with a third-party mirror unless explicitly approved.

## ITM-003: 32-bit PrintDlgW / SplWow64 Green-Box Hang

Source issue: `https://github.com/sandboxie-plus/Sandboxie/issues/4356`

Official API baseline:

- `PRINTDLGW` is the Win32 common-dialog structure used by `PrintDlgW`.
- Microsoft documents `Splwow64.exe` as the process used for 32-bit printing
  compatibility on 64-bit systems.
- Microsoft documents printing RPC connectivity as an RPC endpoint-mapper /
  print-spooler boundary, so this issue must be treated as a WoW64 print RPC
  topology question, not a generic GUI hang.

Repro claim:

```text
Compile the provided PrintDlgW program as 32-bit.
Run it in a green Application Compartment.
The program hangs for around one minute, then returns an error.
```

Hypothesis slot:

```text
H: Green-box compartment mode does not apply the SplWow64 endpoint adjustment
   that yellow-box mode applies, so the 32-bit client waits for an RPC endpoint
   name that does not match the SplWow64 server endpoint.
Condition C: 32-bit PrintDlgW repro runs in New_Box with NoSecurityIsolation=y.
Predicted E: Runtime takes around 60 seconds and SbieSvc / process evidence
   shows SplWow64 or print/RPC endpoint activity before PrintDlgW returns false.
Actual: pending
Owner: pending, likely Sandboxie/core/dll/ipc.c SplWow64 endpoint adjustment path
Next action: Build and run a 32-bit repro executable on the Windows VM.
```

Test runs:

| Run | Build | Box Config | Action | Expected | Actual | Evidence |
|---|---|---|---|---|---|---|
| ITM-003-A | local SREV-037/SREV-279/SREV-299 build, `NAME_BUFFER_DEBUG` disabled | `New_Box`, `NoSecurityIsolation=y` | Run 32-bit `PrintDlgW` repro with timeout and event capture | Around one minute delay or clean failure path with logs | pending | pending |
