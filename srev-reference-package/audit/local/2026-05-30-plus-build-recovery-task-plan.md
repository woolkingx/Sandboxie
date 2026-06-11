# Sandboxie Plus Build Recovery Task Plan

Goal: recover the Windows VM build flow without drifting away from the project
documentation, then produce the smallest verified artifact that supports local
Sandboxie testing.

Architecture: The Linux worktree remains the source owner. The Windows VM is
only a disposable build target that receives source snapshots or targeted file
updates, emits logs under `C:\work\logs`, and never becomes the only truth
owner. Build work follows the documented path: first prove core `x64` build
targets from `docs/plan/local/windows-test-vm-requirements.md`, then build
Sandboxie Plus UI from `SandboxiePlus/ReadMe.md`, and only after those pass
attempt installer packaging from `Installer/ReadMe.md` / `.github/workflows/main.yml`.

Tech Stack: Sandboxie C/C++ core, Visual Studio 2022 Build Tools / MSBuild,
Windows SDK/WDK, Qt 6.8.3 from `Installer/buildVariables.cmd`, Inno Setup for
Plus installer packaging, OpenSSH-controlled Windows VM.

## Current State

- Linux worktree branch: `audit-kernel-path`.
- Dirty source files from build-surfaced fixes:
  - `Sandboxie/core/dll/guimsg.c`
  - `Sandboxie/core/svc/GuiServer.cpp`
  - `Sandboxie/core/svc/SboxSvc.vcxproj`
- Local-only `.cleanup/` contains VM helper scripts and logs; it is not a
  project artifact and must not be staged.
- VM reachable by SSH at `192.168.213.80` as `vboxuser`.
- Tooling already installed/provisioned on the VM during this session:
  - Visual Studio Build Tools through `C:\BuildTools\Common7\Tools\VsDevCmd.bat`
  - 7-Zip
  - Qt 6.8.3 x64 under `C:\work\Qt`
  - Qt 6.8.3 x64 under `C:\work\Qt`
  - Inno Setup current version because the documented 6.3.3 direct URL was no
    longer reachable
- Known deviation to correct: ad-hoc wrapper scripts in `.cleanup/` are allowed
  only as local probes. The execution path must be reduced back to documented
  MSBuild / project script commands.

## File Map

| File | Role |
|---|---|
| `docs/plan/local/windows-test-vm-requirements.md` | Local VM truth owner for first build gates and non-goals |
| `SandboxiePlus/ReadMe.md` | Plus build overview: Classic/core first, then SandMan UI, then combine |
| `Installer/ReadMe.md` | Plus installer owner surface: Inno Setup + `Sandboxie-Plus.iss` |
| `.github/workflows/main.yml` | Most current automated build topology for x64 Qt6 CI |
| `Sandboxie/core/dll/guimsg.c` | Candidate source fix for `BOOL` return narrowing surfaced by `SbieRelease|x64` |
| `Sandboxie/core/svc/GuiServer.cpp` | Candidate source fix for `UnpackDDElParam` parameter type in Win32 Release |
| `Sandboxie/core/svc/SboxSvc.vcxproj` | Candidate project fix for `/utf-8` in Release configs |
| `Sandboxie/apps/control/Control.vcxproj` | Candidate project fix for `/utf-8` in `SbieRelease|x64` after `AboutDialog.cpp` `\u00A9` C4566 surfaced under `/WX` |
| `C:\work\logs\*.log` | Windows build evidence owner |

## Stop Rules

- Stop before source mutation unless the API shape and local owner are named.
- Stop after two failed attempts on the same command and reread the owner docs
  plus the failing log.
- Do not keep adding wrapper behavior to hide toolchain mismatch. A wrapper is
  allowed only when it adapts the VM to the documented command shape and is
  explicitly local-only.
- Do not claim Plus installer readiness until `Installer\SbiePlus_x64` exists
  and either `Sandboxie-Plus-*.exe` exists or the exact Inno/asset blocker is
  recorded.
- Do not stage `.cleanup/`.

## Task Plan

- [x] Step 1: Freeze and classify the current diff.
  - Command:
    ```bash
    git diff -- Sandboxie/core/dll/guimsg.c Sandboxie/core/svc/GuiServer.cpp Sandboxie/core/svc/SboxSvc.vcxproj
    git diff --check
    ```
  - Expected result: diff contains only build/API-shape fixes; whitespace check
    exits 0.
  - Acceptance gate: each changed source line has a named API owner:
    `PostMessageA/W` returns `BOOL`, `UnpackDDElParam` takes `PUINT_PTR`, and
    `/utf-8` is a project encoding build flag.

- [x] Step 2: Run the documented local VM readiness probe before more build work.
  - Command:
    ```bash
    python3 docs/plan/local/windows-vm-readiness-probe.py --host 192.168.213.80 --user vboxuser
    ```
  - Expected result: probe reports SSH reachable and lists any missing required
    VM tools.
  - Acceptance gate: if `msbuild`, `cl`, `link`, SDK/WDK, or test-signing
    prerequisites are missing, stop and update this plan before compiling.
  - Current readback note: the default SSH/PowerShell PATH may not include
    Visual Studio developer tools. If `msbuild`, `cl`, or `link` are missing
    from the default PATH but `C:\BuildTools\Common7\Tools\VsDevCmd.bat` exists,
    run this developer-PATH readback before compiling:
    ```cmd
    @echo off
    call C:\BuildTools\Common7\Tools\VsDevCmd.bat -arch=x64 -host_arch=x64
    where msbuild
    where cl
    where link
    ```
    Copy this local probe to `C:\work\scripts\read-dev-path.cmd` and run:
    ```bash
    ssh -o BatchMode=yes -o ConnectTimeout=8 vboxuser@192.168.213.80 'cmd /c C:\work\scripts\read-dev-path.cmd'
    ```
  - Developer-PATH acceptance gate: `where msbuild`, `where cl`, and
    `where link` all print tool paths after `VsDevCmd.bat`. If not, stop and
    provision Visual Studio Build Tools instead of compiling.
  - Test-signing note: `testsigning No` blocks driver load/runtime smoke, not
    source build. Do not run install/load smoke until test signing is enabled
    and read back.

- [x] Step 3: Sync only the intentional source diff to the VM.
  - Commands:
    ```bash
    scp Sandboxie/core/dll/guimsg.c vboxuser@192.168.213.80:C:/work/sandboxie/Sandboxie/core/dll/guimsg.c
    scp Sandboxie/core/svc/GuiServer.cpp vboxuser@192.168.213.80:C:/work/sandboxie/Sandboxie/core/svc/GuiServer.cpp
    scp Sandboxie/core/svc/SboxSvc.vcxproj vboxuser@192.168.213.80:C:/work/sandboxie/Sandboxie/core/svc/SboxSvc.vcxproj
    ```
  - Expected result: `scp` exits 0.
  - Acceptance gate: no wholesale source reset and no `.cleanup/` file is copied
    as project truth.

- [x] Step 4: Prove the first documented Windows build gate: `SbieDebug|x64`.
  - Windows command through SSH:
    ```cmd
    call C:\BuildTools\Common7\Tools\VsDevCmd.bat -arch=x64 -host_arch=x64
    cd /d C:\work\sandboxie\Sandboxie
    msbuild .\core\low\LowLevel.vcxproj /m /p:Configuration=SbieRelease /p:Platform=Win32
    msbuild .\SandboxDrv.sln /m /p:Configuration=SbieDebug /p:Platform=x64
    msbuild .\SandboxDll.sln /m /p:Configuration=SbieDebug /p:Platform=x64
    ```
  - Expected result: both documented debug targets exit 0; logs are saved under
    `C:\work\logs`.
  - OpenSSH execution note: because the VM OpenSSH default shell is PowerShell,
    copy the command block as a local-only `C:\work\scripts\step4-sbie-debug-x64.cmd`
    and run it through `cmd /c` to avoid shell quoting changing the command.
  - Acceptance gate: `Sandboxie\Bin\x64\SbieDebug\SbieDrv.sys`,
    `SbieDll.dll`, and `SbieSvc.exe` exist or the exact failing compiler/linker
    error is captured.

- [x] Step 5: Prove the second documented Windows build gate: `SbieRelease|x64`.
  - Windows command through SSH:
    ```cmd
    call C:\BuildTools\Common7\Tools\VsDevCmd.bat -arch=x64 -host_arch=x64
    cd /d C:\work\sandboxie\Sandboxie
    msbuild .\Sandbox.sln /m /p:Configuration=SbieRelease /p:Platform=x64
    msbuild .\SandboxDrv.sln /m /p:Configuration=SbieRelease /p:Platform=x64
    ```
  - Expected result: x64 Release core exits 0.
  - OpenSSH execution note: copy the command block as a local-only
    `C:\work\scripts\step5-sbie-release-x64.cmd` and run it through `cmd /c`
    for the same shell-boundary reason as Step 4.
  - Acceptance gate: `Sandboxie\Bin\x64\SbieRelease\SbieDrv.sys`,
    `SbieDll.dll`, `SbieSvc.exe`, `Start.exe`, and `KmdUtil.exe` exist, or the
    exact failing compiler/linker error is captured.
  - Current blocker note: first run failed in
    `Sandboxie/apps/control/AboutDialog.cpp:159` because `Control.vcxproj`
    `SbieRelease|x64` compiled Unicode copyright literals without `/utf-8`;
    `/WX` converted warning C4566 into error C2220. The legal owner is the
    project encoding flag, not the source literal.

- [x] Step 6: Decide whether Win32 Release is required before packaging.
  - Readback command:
    ```bash
    sed -n '150,180p' Installer/copy_build.cmd
    ```
  - Expected result: `copy_build.cmd x64` requires Win32 `SbieSvc.exe` and
    `SbieDll.dll` for the `32\` subdirectory.
  - Acceptance gate: if the target is "portable x64 test folder only", do not
    block on Win32. If the target is "real Plus installer", build Win32 DLL/Svc
    as a required packaging subtask.
  - Decision: the active user target is a real Plus installer/package, so Win32
    DLL/Svc is required before `Installer\copy_build.cmd x64 build_qt6`.

- [x] Step 6a: Build Win32 Release DLL/Svc required by x64 Plus packaging.
  - Windows command:
    ```cmd
    call C:\BuildTools\Common7\Tools\VsDevCmd.bat -arch=x86 -host_arch=x86
    cd /d C:\work\sandboxie\Sandboxie
    msbuild .\SandboxDll.sln /m /p:Configuration=SbieRelease /p:Platform=Win32
    ```
  - Expected result: Win32 Release DLL/Svc exits 0.
  - Acceptance gate: `Sandboxie\Bin\Win32\SbieRelease\SbieSvc.exe` and
    `Sandboxie\Bin\Win32\SbieRelease\SbieDll.dll` exist, or the exact failing
    compiler/linker error is captured.

- [x] Step 7: Build Plus UI only after core x64 Release is proven.
  - Windows command:
    ```cmd
    call C:\BuildTools\Common7\Tools\VsDevCmd.bat -arch=x64 -host_arch=x64
    cd /d C:\work\sandboxie
    SandboxiePlus\qmake_plus.cmd x64 build_qt6
    ```
  - Expected result: `SandboxiePlus\Bin\x64\Release\SandMan.exe`,
    `MiscHelpers.dll`, `QSbieAPI.dll`, `QtSingleApp.dll`, and
    `UGlobalHotkey.dll` exist.
  - OpenSSH execution note: copy the command block as a local-only
    `C:\work\scripts\step7-plus-ui-x64.cmd` and run it through `cmd /c`.
  - Acceptance gate: if this fails, stop at the first qmake/jom compiler error;
    do not patch around Qt until the project file owner is read.
  - Current blocker note: first run reached qmake for `UGlobalHotkey` and then
    failed because `C:\work\Qt\Tools\QtCreator\bin\jom.exe` was missing. This is
    a VM toolchain blocker. Resolve only by running the project-owned
    `SandboxiePlus\install_jom.cmd` (with the local curl compatibility wrapper
    on PATH if the Windows inbox curl lacks `--output-dir`), then rerun Step 7.
  - Resolution note: extracted `jom.exe` into
    `C:\work\Qt\Tools\QtCreator\bin` from the downloaded
    `C:\work\jom_1_1_4.zip`, then reran Step 7. Acceptance gate passed:
    `SandMan.exe`, `MiscHelpers.dll`, `QSbieAPI.dll`, `qtsingleapp.dll`, and
    `UGlobalHotkey.dll` exist under `SandboxiePlus\Bin\x64\Release`.

- [x] Step 8: Build SbieShell and SandboxieTools only after Plus UI exists.
  - Windows command:
    ```cmd
    call C:\BuildTools\Common7\Tools\VsDevCmd.bat -arch=x64 -host_arch=x64
    cd /d C:\work\sandboxie
    msbuild /t:restore,build -p:RestorePackagesConfig=true SandboxiePlus\SbieShell\SbieShell.sln /p:Configuration=Release /p:Platform=x64
    msbuild SandboxieTools\SandboxieTools.sln /m /p:Configuration=Release /p:Platform=x64
    ```
  - Expected result: shell extension package and tools output exist.
  - Acceptance gate: if NuGet or SDK restore fails, record it as a VM tooling
    blocker, not a Sandboxie source blocker.
  - Current blocker note: first run restored NuGet successfully, then
    `SbieShellExt.vcxproj` failed with MSB8036 because the project requests
    Windows SDK `10.0.19041.0` while the VM has SDK `10.0.26100.0`. This is a
    VM toolchain/version adaptation issue. Retry by passing
    `/p:WindowsTargetPlatformVersion=10.0.26100.0` in the local-only Step 8
    script before considering any project-file mutation.
  - Second blocker note: SDK override advanced the build to MSB8020 because
    `SbieShell` and `SbieShellExt` request Visual Studio 2019 toolset `v142`,
    while this VM has the VS2022 `v143` toolchain. CI can use the project
    command on a runner with v142 installed; this VM should adapt locally by
    adding `/p:PlatformToolset=v143` to the Step 8 script. This matches
    `SandboxieTools`, which already uses `v143`.
  - Linker blocker note: after SDK/toolset adaptation, `SbieShellExt.dll` and
    `SbieShellPkg.msix` were produced, then `SbieShell.exe` failed with
    unresolved `WINRT_IMPL_RoGetActivationFactory` and
    `WINRT_IMPL_RoOriginateLanguageException`. Microsoft documents both
    `RoGetActivationFactory` and `RoOriginateLanguageException` as requiring
    `RuntimeObject.lib`. `SbieShellExt.vcxproj` already links
    `runtimeobject.lib`; `SbieShell.vcxproj` should link it too.
  - Resource blocker note: after `SbieShell` passed, `SandboxieTools` failed in
    `UpdUtil.rc` and `ImBox.rc` with RC preprocessor errors. `.gitattributes`
    declares `*.rc` as UTF-8 working-tree encoding, but both files were UTF-16LE
    with mixed line terminators. Normalizing those files to UTF-8 with stable
    line endings made the Step 8 gate pass.
  - Resolution note: Step 8 passed with `SbieShellExt.dll`,
    `SbieShellPkg.msix`, `ImBox.exe`, and `UpdUtil.exe` present.

- [x] Step 9: Combine a local Plus x64 artifact folder.
  - Windows command:
    ```cmd
    call C:\BuildTools\Common7\Tools\VsDevCmd.bat -arch=x64 -host_arch=x64
    cd /d C:\work\sandboxie
    Installer\fix_qt5_languages.cmd x64 build_qt6
    Installer\get_openssl.cmd
    Installer\get_7zip.cmd
    Installer\copy_build.cmd x64 build_qt6
    ```
  - Expected result: `C:\work\sandboxie\Installer\SbiePlus_x64` exists with
    core, Plus UI, Qt, OpenSSL, 7z, templates, and tools.
  - Acceptance gate: this folder is enough for first local install/smoke if the
    installer `.exe` is blocked.
  - Current blocker note: first run failed in `fix_qt5_languages.cmd` because
    the VM's default `curl` does not support `--output-dir`. This is a VM
    tooling compatibility issue. Resolve in the local-only Step 9 script by
    running the equivalent Qt translation download/extract/lrelease commands
    with `curl -o` before returning to the project-owned OpenSSL, 7-Zip, and
    `copy_build.cmd` scripts. Do not shadow `curl` with a `.cmd` wrapper:
    batch-to-batch invocation without `call` prevents `get_openssl.cmd`
    fallback branches from returning to the caller.
  - Batch parser note: keep the Qt translation compatibility commands in a
    separate local-only `.cmd`; placing `set PATH=...Program Files (x86)...`
    inside a parenthesized logging block makes `cmd.exe` parse the `(x86)` path
    segment as syntax.
  - Resolution note: Step 9 passed. `Installer\SbiePlus_x64` contains
    `SandMan.exe`, `SbieDrv.sys`, `SbieDll.dll`, `32\SbieDll.dll`,
    `SbieShellExt.dll`, `ImBox.exe`, and `UpdUtil.exe`.

- [x] Step 10: Attempt Inno installer only after `SbiePlus_x64` is complete.
  - Windows command:
    ```cmd
    cd /d C:\work\sandboxie\Installer
    mkdir Release
    xcopy /E /I /Y SbiePlus_x64 Release\SbiePlus64
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" /ORelease Sandboxie-Plus.iss /DMyAppVersion=1.17.7 /DMyAppArch=x64 /DMyAppSrc=SbiePlus64
    ```
  - Expected result: `C:\work\sandboxie\Installer\Release\Sandboxie-Plus-x64-v1.17.7.exe`.
  - Acceptance gate: if Inno fails, preserve the log and keep
    `Installer\SbiePlus_x64` as the first usable artifact.
  - Local signing note: this VM does not own a release signing certificate. For
    a local test installer only, define Inno's `sha256` sign tool as a no-op in
    the Step 10 script so `SignTool=sha256` does not block packaging. Any
    resulting installer is unsigned and not a release artifact.
  - Inno sign-tool shape note: the no-op `sha256` command still must contain
    Inno's `$f` file placeholder; otherwise ISCC aborts with "Unable to run
    Sign Tool sha256: $f sequence is missing."
  - Inno signature verification note: Inno Setup 6.7.1 rejects a no-op sign
    tool even when it exits 0 because the target file remains unsigned. For
    local testing, generate `Sandboxie-Plus.local-nosign.iss` on the VM with
    only `SignTool=sha256` commented out, and compile that local copy. Do not
    modify the source `Sandboxie-Plus.iss`.
  - ImDisk payload note: the source tree/VM does not currently contain
    `imdisk_files.cab` or `imdisk_install.bat`. These are optional installer
    payloads for the ImDisk task, not required for the local core/UI smoke
    target. The local unsigned `.iss` copy may also comment out the ImDisk task,
    source file entries, and run entry. A release installer still requires the
    real ImDisk payloads.
  - Resolution note: Step 10 passed and produced unsigned local test installer
    `Installer\Release\Sandboxie-Plus-x64-v1.17.7.exe`.

- [x] Step 11: Pull logs and artifacts back to Linux.
  - Commands:
    ```bash
    mkdir -p .cleanup/windows-logs .cleanup/windows-artifacts
    scp -r vboxuser@192.168.213.80:C:/work/logs/* .cleanup/windows-logs/
    scp -r vboxuser@192.168.213.80:C:/work/sandboxie/Installer/SbiePlus_x64 .cleanup/windows-artifacts/ 2>/dev/null || true
    scp -r vboxuser@192.168.213.80:C:/work/sandboxie/Installer/Release .cleanup/windows-artifacts/ 2>/dev/null || true
    ```
  - Expected result: logs and any produced artifacts are available under
    `.cleanup/`.
  - Acceptance gate: final status references local log/artifact paths and does
    not claim success from oral output.
  - Resolution note: logs were pulled to `.cleanup/windows-logs/`; the local
    Plus folder and installer release tree were pulled to
    `.cleanup/windows-artifacts/`.

- [ ] Step 12: Commit only verified source/doc changes as backup.
  - Commands:
    ```bash
    git status --short
    git add docs/plan/local/2026-05-30-plus-build-recovery-task-plan.md
    git add Sandboxie/core/dll/guimsg.c Sandboxie/core/svc/GuiServer.cpp Sandboxie/core/svc/SboxSvc.vcxproj Sandboxie/apps/control/Control.vcxproj SandboxiePlus/SbieShell/SbieShell/SbieShell.vcxproj SandboxieTools/UpdUtil/UpdUtil.rc SandboxieTools/ImBox/ImBox.rc
    git diff --cached --check
    git commit -m "fix: restore release build gates"
    ```
  - Expected result: commit succeeds only after the Windows build gate that
    requires the source changes has passed.
  - Acceptance gate: `.cleanup/` remains untracked and unstaged.

## Self-Review

- Spec coverage: Covers VM requirements, Plus build docs, installer docs,
  current dirty source, local artifact/log flow, and stop rules.
- Placeholder scan: No placeholder steps; each command has an expected result
  and acceptance gate.
- Type consistency: Paths use existing repository and VM paths; build
  configurations match project docs and CI workflow.
- Known gap: Inno Setup current version was installed because 6.3.3 direct
  archive URL was not reachable. If exact 6.3.3 becomes mandatory, pause and
  provision it from a verified source before Step 10.
