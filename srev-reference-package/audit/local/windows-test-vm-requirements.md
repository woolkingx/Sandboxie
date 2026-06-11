# Windows Test VM Requirements For Sandboxie Local Validation

This document is for provisioning a disposable Windows VM that Codex can control
without manual steps. It is local/private infrastructure for validating this
fork. It is not an upstream SREV/KPATH artifact.

## Core Principle

The agent control plane must stay outside the tested Windows OS.

```text
Linux/PVE controller
  -> owns git source, snapshots, VM power state, artifact transfer, log pickup

Windows test VM
  -> builds, signs, installs, runs Sandboxie tests, emits logs/artifacts
```

Codex Desktop may be installed inside the Windows VM as a convenience, but it
must not be the only controller. If the driver hangs or the VM bugchecks, the
outside controller must be able to reboot or roll back the VM.

## Required Topology

| Layer | Requirement |
|---|---|
| Host | Proxmox VE or another controller that can start, stop, snapshot, roll back, and copy files to/from the VM without using the VM desktop |
| VM role | Disposable Windows test target, not the only source-code owner |
| Source owner | Git source remains on the Linux/controller side or is mirrored from it |
| Artifact flow | Controller pushes source/artifacts to `C:\work\sandboxie`, runs scripts remotely, pulls logs from `C:\work\logs` |
| Recovery | Test run starts from a known snapshot and may roll back automatically |
| Human use | No manual clicking should be required after provisioning |

## VM Baseline

Recommended first VM:

| Item | Requirement |
|---|---|
| OS | Windows 11 x64 or Windows 10 x64, fully updated enough to install VS/WDK |
| CPU | 4 vCPU minimum, 8 vCPU preferred |
| RAM | 16 GB minimum, 32 GB preferred |
| Disk | 120 GB minimum, 200 GB preferred, snapshot-capable |
| Network | Private LAN reachable from controller; internet access for initial tool install |
| Firmware | Secure Boot disabled for test-signing work |
| HVCI / Memory Integrity | Disabled for first bring-up; can be enabled later as a separate matrix |
| Checkpoint | Snapshot named `clean-tools-installed` after all tools and remote access are verified |

Install the QEMU guest agent if this is a PVE VM.

## Required Remote Control

Install and enable at least one remote command channel. OpenSSH is preferred
because the Linux controller can drive it directly.

Required:

- OpenSSH Server enabled and reachable from the controller.
- Admin test account, for example `sbie-test`.
- SSH public-key authentication for the controller.
- PowerShell remoting optional but useful.
- Windows Firewall rules allowing the chosen remote channel only from the
  controller LAN/IP.

Acceptance checks from controller:

```bash
ssh sbie-test@<vm-ip> 'hostname'
ssh sbie-test@<vm-ip> 'powershell -NoProfile -Command "$PSVersionTable.PSVersion"'
```

## Required Windows Tools

Install these in the Windows VM:

| Tool | Requirement |
|---|---|
| Visual Studio 2022 | Community/Professional/Enterprise or Build Tools 2022. Do not use VS 2026 for driver development at this time. |
| MSVC | v143 C++ tools for x64/x86. Add ARM64/ARM64EC only if that matrix is needed. |
| C++ workload | Desktop development with C++ |
| ATL/MFC | Latest v143 ATL and MFC with Spectre mitigations for x64/x86 |
| Windows SDK | Installed SDK version must match the WDK build number |
| WDK | Windows Driver Kit matching the SDK; include Visual Studio WDK component/VSIX |
| Debugging Tools | WinDbg / Debugging Tools for Windows |
| PowerShell | PowerShell 7 plus built-in Windows PowerShell |
| Git | Git for Windows, with long paths enabled |
| Python | Python 3.11+ x64, available on PATH |
| Sysinternals | Handle, ProcDump, Process Explorer, ProcMon; unpack under `C:\Tools\Sysinternals` |
| NSIS | Optional for installer packaging; not required for first driver/DLL/service smoke |
| 7-Zip | Optional but useful for artifact packaging |
| Codex Desktop | Optional helper inside VM; not the recovery/control owner |

Official Microsoft references:

- WDK download / VS 2022 requirement: `https://learn.microsoft.com/en-us/windows-hardware/drivers/download-the-wdk`
- WDK install with WinGet: `https://learn.microsoft.com/en-us/windows-hardware/drivers/install-the-wdk-using-winget`
- Enable loading test-signed drivers: `https://learn.microsoft.com/en-us/windows-hardware/drivers/install/the-testsigning-boot-configuration-option`
- Test-signing a driver file: `https://learn.microsoft.com/en-us/windows-hardware/drivers/install/test-signing-a-driver-file`

## Required Paths

Create these directories:

```text
C:\work\sandboxie       # source checkout or controller-synced source
C:\work\artifacts       # build outputs copied for install/test
C:\work\logs            # all test logs, event exports, dumps, command output
C:\work\scripts         # helper scripts controlled by repo/controller
C:\Tools                # Sysinternals, helper binaries, optional tools
```

Enable long paths:

```powershell
git config --global core.longpaths true
New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" `
  -Name LongPathsEnabled -Value 1 -PropertyType DWord -Force
```

## Test Signing Setup

The Windows loader signature gate cannot be bypassed by Sandboxie code. The VM
must be configured so Windows accepts test-signed kernel drivers.

Required:

```powershell
bcdedit /set testsigning on
```

Then reboot and verify the desktop shows test mode or read back:

```powershell
bcdedit /enum | findstr /i testsigning
```

Create/import a local test certificate for signing artifacts. The exact cert
name can change, but use a clear local-only name:

```powershell
$cert = New-SelfSignedCertificate `
  -Type CodeSigningCert `
  -Subject "CN=Sandboxie Local Test Driver" `
  -CertStoreLocation "Cert:\LocalMachine\My"

Export-Certificate -Cert $cert -FilePath C:\work\artifacts\sandboxie-local-test.cer
Import-Certificate -FilePath C:\work\artifacts\sandboxie-local-test.cer `
  -CertStoreLocation "Cert:\LocalMachine\Root"
Import-Certificate -FilePath C:\work\artifacts\sandboxie-local-test.cer `
  -CertStoreLocation "Cert:\LocalMachine\TrustedPublisher"
```

The test VM must expose the installed cert thumbprint to scripts:

```powershell
Get-ChildItem Cert:\LocalMachine\My |
  Where-Object Subject -eq "CN=Sandboxie Local Test Driver" |
  Select-Object Subject, Thumbprint, NotAfter
```

## Sandboxie Build Targets

Known local build surfaces from this repo:

```text
Sandboxie\Sandbox.sln
Sandboxie\SandboxDrv.sln
Sandboxie\SandboxDll.sln
Sandboxie\core\drv\SboxDrv.vcxproj
Sandboxie\core\dll\SboxDll.vcxproj
Sandboxie\core\svc\SboxSvc.vcxproj
Sandboxie\install\kmdutil\kmdutil.vcxproj
Sandboxie\install\build.bat
```

First target:

```text
SbieDebug|x64
```

Then:

```text
SbieRelease|x64
```

Win32, ARM64, and ARM64EC are later matrix items. Do not block the first VM on
them unless the assigned task explicitly requires them.

## Required Readback Commands

After provisioning, these commands must work from an elevated Developer
PowerShell or Developer Command Prompt:

```powershell
where git
where python
where pwsh
where msbuild
where cl
where link
where signtool
where inf2cat
where windbg
```

Visual Studio discovery:

```powershell
& "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe" `
  -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 `
  -property installationPath
```

Build smoke:

```powershell
cd C:\work\sandboxie\Sandboxie
msbuild .\SandboxDrv.sln /m /p:Configuration=SbieDebug /p:Platform=x64
msbuild .\SandboxDll.sln /m /p:Configuration=SbieDebug /p:Platform=x64
```

If the repo needs a specific VS developer environment, create a wrapper script
that calls the discovered `VsDevCmd.bat` before `msbuild`.

## Required Test Mode Configuration

For this fork only, the VM should be able to enable the local test gate:

```ini
[GlobalSettings]
Test=true
```

This is local-only. It bypasses Sandboxie's own test verification gates but does
not bypass Windows driver loading policy.

## Required Logging And Crash Artifacts

Enable artifact collection before driver smoke tests:

| Artifact | Path / command |
|---|---|
| Command logs | Save every build/test command output under `C:\work\logs` |
| Event logs | Export System and Application logs after each run |
| Driver crash dumps | Configure kernel/full memory dumps if disk allows |
| User dumps | Configure WER LocalDumps for Sandboxie processes |
| ProcDump | Available under `C:\Tools\Sysinternals` |
| WinDbg | Installed and callable for dump triage |

Minimum event export commands:

```powershell
wevtutil epl System C:\work\logs\System.evtx
wevtutil epl Application C:\work\logs\Application.evtx
```

## Snapshot Contract

Provisioner must create these snapshots:

| Snapshot | When |
|---|---|
| `clean-os` | After Windows install, updates, network, and guest agent |
| `clean-tools-installed` | After VS/SDK/WDK/tools/SSH are verified |
| `clean-testsigning-enabled` | After testsigning, cert import, reboot, and readback |
| `pre-sandboxie-smoke` | Before first driver install/load smoke |

The outside controller must be able to:

```text
stop VM
start VM
reboot VM
roll back to snapshot
detect VM reachability by SSH
copy artifacts out after a run
```

## Acceptance Checklist

The VM is ready only when all are true:

- Controller can run PowerShell commands over SSH without opening the VM desktop.
- Controller can reboot and regain SSH access.
- Controller can roll back to `clean-testsigning-enabled`.
- `msbuild`, `cl`, `link`, `signtool`, `inf2cat`, and `windbg` are on a usable developer PATH.
- Visual Studio 2022 + SDK + WDK are installed; SDK and WDK build numbers match.
- `bcdedit /enum` shows `testsigning Yes`.
- Local code-signing cert is present in `LocalMachine\My`, `Root`, and `TrustedPublisher`.
- `Sandboxie\SandboxDrv.sln` builds `SbieDebug|x64` or produces a clear build log under `C:\work\logs`.
- `Sandboxie\SandboxDll.sln` builds `SbieDebug|x64` or produces a clear build log under `C:\work\logs`.
- `C:\work\logs` can be copied back to the controller.

## Non-Goals

- Do not put the only git source copy inside the Windows test VM.
- Do not rely on Codex Desktop inside the VM for crash recovery.
- Do not enable `Test=true` in any upstream PR branch.
- Do not test first on a daily-use Windows system.
- Do not install random driver/security tools that add filter drivers unless a
  specific compatibility matrix requires them.
