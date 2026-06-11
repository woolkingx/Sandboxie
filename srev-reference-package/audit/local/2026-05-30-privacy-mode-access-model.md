---
kind: local-research-note
id: LMODEL-PRIVACY-ACCESS-001
title: Privacy Mode Access Permission Model
status: source-level-and-runtime-smoke-observed
owner: Sandboxie/core/drv/process.c
scope: local runtime testing and issue triage
---

# Privacy Mode Access Permission Model

Goal: preserve the source-level access model for `UsePrivacyMode=y` before
runtime testing privacy-enhanced boxes.

## Owner Path

```text
Sandboxie.ini [Box] UsePrivacyMode=y
  -> Process_Create
  -> proc->use_privacy_mode = TRUE
  -> proc->use_rule_specificity = TRUE
  -> File_InitPaths / Key_InitProcess
  -> Process_MatchPathEx
  -> file/key create/open decision
```

Primary owner files:

- `Sandboxie/core/drv/process.c`
- `Sandboxie/core/drv/file.c`
- `Sandboxie/core/drv/key.c`
- `Sandboxie/core/drv/process_util.c`
- `Sandboxie/install/Templates.ini`
- `SandboxiePlus/SandMan/Views/NtObjectView.cpp`

## Core Semantics

`UsePrivacyMode=y` is not primarily a Windows token or ACL model. It is a path
permission matrix over true host paths and sandbox copy paths.

The driver path flags are:

```text
TRUE_PATH_CLOSED  = 0x00
TRUE_PATH_READ    = 0x10
TRUE_PATH_WRITE   = 0x20
TRUE_PATH_OPEN    = 0x30

COPY_PATH_CLOSED  = 0x00
COPY_PATH_READ    = 0x01
COPY_PATH_WRITE   = 0x02
COPY_PATH_OPEN    = 0x03
```

The default normal-mode decision remains:

```text
TRUE_PATH_READ | COPY_PATH_OPEN
```

Privacy mode does not currently switch the global default in
`Process_MatchPathEx`; the older closed-by-default branch is commented out.
Instead, privacy mode injects explicit write/normal rule sets through
`TemplatePModPaths` and drive-path rules.

## Privacy Mode Rule Injection

When privacy mode is active:

- `Process_Create` forces `use_rule_specificity`.
- `Process_GetTemplatePaths` loads `TemplatePModPaths`.
- `File_InitPaths` adds drive device patterns to `WriteFilePath`.
- `Key_InitProcess` adds `\REGISTRY\USER\*` to `WriteKeyPath`.
- `TemplatePModPaths` restores selected OS/program paths through
  `NormalFilePath` / `NormalKeyPath`.

Important source evidence:

```text
Templates.ini [TemplatePModPaths]
WriteKeyPath=\REGISTRY\USER\*
NormalFilePath=%SystemRoot%\*
NormalFilePath=%SbieHome%\*
NormalFilePath=%ProgramFiles%\*
NormalFilePath=%ProgramFiles% (x86)\*
NormalFilePath=%ProgramData%\Microsoft\*
WriteFilePath=?:\$Recycle.Bin\**\*
```

In the UI object model, privacy mode mirrors the same idea:

```text
PMode -> drive paths become BoxOnly
PMode -> RuleSpecificity enabled
```

## Permission Meaning

For files and keys, `Write*Path` means:

```text
TRUE_PATH_CLOSED | COPY_PATH_OPEN
```

The practical result is:

- reading existing host user data is hidden or denied;
- writes/new objects go to the sandbox copy path;
- selected OS/program locations are restored through `Normal*Path`;
- explicit `Open*Path` still means true host path open access;
- explicit `Read*Path` means true host read and sandbox-copy read only.

When driver access evaluation sees no true-path permission:

```text
if TRUE_PATH_MASK == 0:
    if COPY_PATH_WRITE:
        return STATUS_OBJECT_NAME_NOT_FOUND
    else:
        return STATUS_ACCESS_DENIED
```

This matters: privacy mode often hides host data as "not found" so applications
create sandbox-local state, instead of failing with a hard access-denied error.

## Certificate/Test Gate

`UsePrivacyMode=y` is a supporter-gated setting in the driver process gate.
Without a valid certificate and without local `Test=true`, `Process_Create`
logs `SBIE6004` and schedules a 5-minute process kill.

Local `Test=true` bypasses that core driver gate, but SandMan UI may still show
supporter-certificate warnings because the UI certificate check is a separate
surface.

Therefore runtime tests should prove the core gate by checking for absence of:

```text
SBIE6004
SBIE6008
SBIE6009
```

Do not treat the UI warning alone as proof that the driver `Test=true` gate
failed.

## Runtime Test Gates

Minimum privacy-mode smoke:

```text
[GlobalSettings]
Test=true

[Privacy_Box]
UsePrivacyMode=y
```

Run a sandboxed command as an interactive or scheduled user task, then verify:

- no `SBIE6004/6008/6009` in the test window;
- reading a host user file that is covered by privacy write rules appears
  missing or inaccessible from inside the sandbox;
- creating the same path succeeds into the sandbox copy;
- reading `NormalFilePath` OS/program locations still works;
- adding explicit `OpenFilePath` or `ReadFilePath` changes only the intended
  path.

## Runtime Smoke Evidence

Windows VM:

```text
host: 192.168.213.80
box: Privacy_Test
Sandboxie home: C:\temp\Sandboxie-Plus
sandbox root: C:\temp\Sandbox
```

Test configuration:

```text
[GlobalSettings]
Test=true

[Privacy_Test]
Enabled=y
FileRootPath=C:\temp\Sandbox\%SANDBOX%
UsePrivacyMode=y
```

Host sentinel before and after the test:

```text
C:\Users\vboxuser\Documents\privacy-host-sentinel.txt
HOST_SECRET_20260530
```

The first attempted test failed with `START_RC=1` because the inner test script
was stored under `C:\work\privacy-inner.cmd`. Privacy mode hid that host C-drive
path from the sandbox, so the sandboxed `cmd.exe` could not read the script.
This was expected after reading the model and was corrected by moving the inner
script to `C:\temp\Sandboxie-Plus\privacy-inner.cmd`, a normal program path.

Successful scheduled-task smoke:

```text
OUTER_START 2026/05/30 15:51:36
TERM_RC=0
START_RC=0
OUTER_END 2026/05/30 15:51:40
```

Sandboxed result:

```text
READ_ATTEMPT
The system cannot find the file specified.
READ_RC=1
WRITE_RC=1
AFTER_WRITE_READ
SANDBOX_WRITE_20260530
AFTER_READ_RC=0
```

Observed sandbox copy paths:

```text
C:\temp\Sandbox\Privacy_Test\user\current\Documents\privacy-host-sentinel.txt
C:\temp\Sandbox\Privacy_Test\user\current\Documents\privacy-test-result.txt
```

Interpretation:

- privacy mode hid the host `Documents` sentinel on first read;
- the host sentinel remained unchanged;
- the sandboxed write materialized under the sandbox user-copy tree;
- no `SBIE6004`, `SBIE6008`, or `SBIE6009` supporter-certificate gate event was
  observed in the test window, so local `Test=true` was sufficient for the core
  driver gate;
- SandMan UI supporter warnings are a separate UI layer and are not proof that
  the core driver test gate failed.

## Open Questions

- Which exact user-data roots should be part of privacy mode by default on the
  current Windows build?
- Whether `TemplatePModPaths` is too broad or too narrow for modern profile
  locations such as OneDrive, Known Folders, browser profiles, and AppContainer
  data.
- Whether UI warnings should honor local `Test=true` for disposable developer
  builds, or remain intentionally separate from core driver testing.
