# SREV-085: PCA Restart Command-Line Shape

## Data

`Sandboxie/core/dll/dllmain.c` detects early process-start compatibility states.
The relevant comment-admitted states in this file are:

```text
Digital Guardian compatibility module detection
Program Compatibility Assistant job detection
AppContainer exclusion for PCA restart
forced-process restart policy
restart command line and current directory payload
service-owned RunSandboxed process creation
```

`Sandboxie/core/dll/proc.c` owns the restart payload in
`Proc_RestartProcessOutOfPcaJob`.

## Official Shape

Microsoft documents job objects as process-group control objects. Once a
process is associated with a job object, child processes created with
`CreateProcess` are associated with that job by default. Windows versions before
Windows 8 do not support nested jobs.

Microsoft documents `AssignProcessToJobObject` as failing for an already-jobbed
process on Windows versions before Windows 8 / Windows Server 2012. On newer
Windows builds, an already-jobbed process may join another job only if the
nested job hierarchy is valid.

Microsoft documents `GetCommandLineW` as returning a pointer to the current
process command-line string. The returned value is system-owned and must not be
modified or freed by the application.

Microsoft documents `CreateProcessW` as consuming a mutable command-line buffer
when `lpApplicationName` is NULL. The Sandboxie restart path forwards the copied
command line into its service-owned `RunSandboxed` process-creation boundary.

Microsoft documents `GetCurrentDirectory` as a variable-length API: callers can
query the required buffer size, and an undersized buffer returns the required
size rather than a complete directory.

```text
https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects
https://learn.microsoft.com/en-us/windows/win32/procthread/nested-jobs
https://learn.microsoft.com/en-us/windows/win32/api/jobapi2/nf-jobapi2-assignprocesstojobobject
https://learn.microsoft.com/en-us/windows/win32/api/processenv/nf-processenv-getcommandlinew
https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-createprocessw
https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-getcurrentdirectory
```

## Schema

Local schema:

```text
docs/plan/srev-085-pca-restart-command-line-shape.schema.json
```

The restart contract is:

```text
PCA/job detection decides whether restart is needed before sandbox job attach
AppContainer processes do not use the PCA restart path
GetCommandLine returns system-owned read-only input
restart command line storage is sized from the actual command-line length
the restart payload must not copy a variable-length command line into a fixed local buffer
Digital Guardian detection remains an early module-presence compatibility flag
```

## Topology

```text
driver process flags
  -> dllmain PCA / forced-process restart decision
  -> Proc_RestartProcessOutOfPcaJob restart payload
  -> SbieDll_RunSandboxed request
  -> SbieSvc ProcessServer RunSandboxedStartProcess
  -> CreateProcessAsUser / driver API_START_PROCESS sandbox attach
```

The restart logic belongs at the SbieDll process-start boundary because the
original process is already in the incompatible PCA job. The service remains the
owner of creating the replacement process and attaching it to the sandbox.
SREV-262 later clarified the `dllmain.c` source comment so the PCA restart
topology points at this SREV owner instead of a generic workaround label.

## Logic Risk

The PCA workaround itself matches the official job-object topology: on older
Windows builds a process already associated with PCA's job cannot simply be
assigned to Sandboxie's job; on newer builds, the existing PCA job can still be
an invalid hierarchy for Sandboxie's job policy. Restarting through SbieSvc is a
transport strategy for producing a replacement process outside the PCA job.

Before this patch, `Proc_RestartProcessOutOfPcaJob` copied the current process
command line into a fixed 8192-WCHAR temporary buffer with `wcscpy`. The
official `GetCommandLineW` shape is variable-length system-owned input, and the
restart path forwards that payload into process creation. Treating that payload
as a fixed local buffer risks corrupting the restart path before the service
owner ever receives a valid command line.

The Digital Guardian lines in `dllmain.c` are also comment-admitted compatibility
state. They are classified here as module-presence detection only: `dllmain.c`
sets the early flag with `GetModuleHandleA`, while `file.c` and `ldr.c` consume
the flag/module-init state. This SREV does not change that third-party policy.

## Fix

`Proc_RestartProcessOutOfPcaJob` now treats `GetCommandLine` output as
system-owned input, measures the actual string length, checks byte-size overflow
against `Dll_AllocTemp`'s `ULONG` byte-size boundary, allocates exactly enough
storage for the terminating NUL, and copies with `memcpy`.

## Acceptance Gate

`docs/plan/check-srev-085.py` validates the draft-07 schema, official
references, `dllmain.c` PCA/AppContainer restart gate and SREV-085 comment
owner, Digital Guardian
classification evidence, dynamic command-line allocation in `proc.c`, stale
fixed command-line buffer removal, and ledger entry.

Windows gate: a forced process launched from a PCA-job parent restarts through
SbieSvc with short and long command lines, AppContainer processes skip the PCA
restart path, and Digital Guardian module detection still drives the existing
file/loader compatibility behavior. Source-level gates do not prove these
runtime paths.
