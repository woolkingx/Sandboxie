# SREV-322: Proc WerFault Dump Suppression Boundary

## Data

`Sandboxie/core/dll/proc.c` creates child processes suspended while it adjusts
their token state. After the token is set, `resume_thread` controls when the
new child thread is resumed. A special WerFault path records whether a WerFault
process was already allowed to run, resumes the first one long enough to collect
a dump, and terminates later WerFault launches to avoid duplicate dump capture.

The relevant data nodes are:

```text
Proc_CreateProcessInternalW
resume_thread
lpApplicationName / WerFault.exe
g_boolWasWerFaultLastProcess
lpProcessInformation->hProcess
lpProcessInformation->hThread
ResumeThread
TerminateProcess
WaitForSingleObject
CloseHandle
SbieApi_Log(2224)
Dump_Init / EnableMiniDump adjacency
```

## Official Shape

Microsoft documents Windows Error Reporting as the component that can write
user-mode dump files when user-mode applications fail. The LocalDumps feature is
configured through Windows Error Reporting registry values and collects the dump
after a crash before normal termination proceeds.

```text
https://learn.microsoft.com/en-us/windows-hardware/drivers/debugger/windows-error-reporting
https://learn.microsoft.com/en-us/windows/win32/wer/collecting-user-mode-dumps
```

Microsoft documents `ResumeThread` as decrementing a thread suspend count and
resuming execution when the count reaches zero.

```text
https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-resumethread
```

Microsoft documents `TerminateProcess` as unconditional process termination. It
is asynchronous when terminating another process; callers that need to know
termination has completed should wait on the process handle.

```text
https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-terminateprocess
```

Microsoft documents `WaitForSingleObject` as waiting for an object to become
signaled or for a timeout, and `CloseHandle` as closing a caller-owned object
handle.

```text
https://learn.microsoft.com/en-us/windows/win32/api/synchapi/nf-synchapi-waitforsingleobject
https://learn.microsoft.com/en-us/windows/win32/api/handleapi/nf-handleapi-closehandle
```

## Schema

Local schema:

```text
docs/plan/srev-322-proc-werfault-dump-suppression-boundary.schema.json
```

`PROC_WERFAULT_DUMP_SUPPRESSION_BOUNDARY` says:

- WerFault dump suppression is local `proc.c` process-lifetime policy;
- WER dump configuration and in-process minidump writing are separate owners;
- the first WerFault process may be resumed and waited for dump capture;
- repeated WerFault processes may be terminated only after the exact WerFault
  predicate and duplicate-state gate;
- duplicate WerFault suppression terminates and waits but keeps
  `PROCESS_INFORMATION` handles caller-owned on the successful create path;
- this source path removes the duplicate-path premature handle close while
  preserving first WerFault and non-WerFault resume behavior.

## Topology

```text
created suspended child process
  -> token fixup
  -> resume_thread gate
  -> WerFault predicate
  -> first WerFault: ResumeThread -> wait for dump capture
  -> repeated WerFault: TerminateProcess -> WaitForSingleObject -> return signaled handles caller-owned
  -> non-WerFault: ResumeThread
```

Adjacent dump topology remains separate:

```text
dllmain.c EnableMiniDump -> Dump_Init -> MiniDumpWriteDump (SREV-156/SREV-237)
Windows Error Reporting -> LocalDumps registry -> WerFault dump capture
```

## Logic Risk

The old comment framed this as a generic WerFault design flaw. The real owner is
more precise: this is a duplicate WerFault process-lifetime suppression gate.
The repeated-WerFault path used to close the process and thread handles while
the surrounding create-process logic still followed an `ok` path. That made the
duplicate process handle no longer caller-visible even though the API surface
still returned success. The source path now removes that premature handle close:
duplicate WerFault is still terminated and waited, but the caller-facing
`PROCESS_INFORMATION` handles remain caller-owned and the duplicate process
handle remains caller-visible in the signaled state.

Windows still needs a crash/WER matrix before release because the matrix must
prove dump timing, duplicate suppression, and caller-visible handle semantics on
real Windows builds. The Linux source review proves the local owner and removes
the wrong local lifetime transition; it does not prove WER runtime behavior.

## Runtime Verification Matrix

The Windows gate must prove both dump correctness and process/handle behavior:

| Axis | Required coverage |
|---|---|
| WER setup | `LocalDumps` enabled globally and for the crashing test executable; dump folder ACL permits the crashing sandboxed process to write |
| Sandbox dump setting | `EnableMiniDump` on and off to prove WER/LocalDumps and Sandboxie's in-process dump owner remain separate |
| Crash source | sandboxed process with a deterministic unhandled exception; repeated crash runs in the same box |
| WerFault observation | count WerFault launches, record first versus duplicate launches, and capture `SbieApi_Log(2224)` |
| First WerFault path | `ResumeThread` path produces the expected dump and waits up to the 30000 ms process-handle gate |
| Duplicate WerFault path | repeated WerFault is terminated, process handle becomes signaled, duplicate process handle remains caller-visible, and returned process/thread handle behavior is observed by the caller |
| Output handles | caller-facing `PROCESS_INFORMATION` handles remain caller-owned on first, duplicate, and non-WerFault success paths |
| Negative controls | non-WerFault suspended child process still resumes normally; WER disabled or LocalDumps absent does not regress normal process creation |
| Regression | Sandboxie's `Dump_Init` / `MiniDumpWriteDump` path from SREV-156/SREV-237 still produces expected in-process dumps when enabled |
| Evidence | dump file path, dump count, WerFault process ids, exit status, wait result, handle validity/readback, Sandboxie log line, Windows build |

## LocalDumps Process-Lifetime Matrix

The Windows gate is not "a dump exists". It must prove the owner and timing of
dump capture, duplicate suppression, and caller-visible process/thread handles.

Required dimensions:

- Windows builds: supported Windows 10 and Windows 11 releases, with build,
  architecture, WER service state, and UAC/elevation context recorded.
- WER configuration: global `LocalDumps`, per-application `LocalDumps`,
  `DumpFolder`, `DumpCount`, `DumpType`, custom dump flags, folder ACL, WER
  disabled, automatic debugging configured, and missing registry keys.
- Sandbox configuration: `EnableMiniDump=y`, `EnableMiniDump=n`, default box,
  restricted token box, and box with blocked write access to the dump folder.
- Crash source: deterministic native crash, repeated crash in same box, crash in
  a process that does custom crash reporting, and non-crashing child process.
- WerFault path: first WerFault process id, duplicate WerFault process ids,
  `SbieApi_Log(2224)`, first `ResumeThread` return value, first wait result,
  duplicate `TerminateProcess` result, duplicate wait result, and duplicate
  process exit code.
- Dump output: file path, file count, file timestamp order, dump type, expected
  process identity, replacement behavior when `DumpCount` is exceeded, and
  absence of dump when WER/LocalDumps is disabled.
- Handle semantics: caller-visible `PROCESS_INFORMATION.hProcess` and
  `hThread` validity after first path, duplicate path, non-WerFault path,
  failed-token-fixup path, and caller `GetExitCodeProcess` /
  `WaitForSingleObject` / `CloseHandle` readback.
- Adjacency regression: SREV-156/SREV-237 in-process `Dump_Init` /
  `MiniDumpWriteDump` output remains independent of WER LocalDumps behavior.

Negative controls:

- non-WerFault suspended child still resumes normally;
- WerFault launched outside the exact predicate is not suppressed;
- WER disabled or LocalDumps absent does not break ordinary process creation;
- automatic debugging configured suppresses LocalDumps as Microsoft documents;
- dump folder ACL denial is reported as no dump output, not a process-lifetime
  policy success;
- duplicate suppression never applies to the first WerFault path in a fresh
  box/session.

## Fix

Source-level local lifetime fix. The source now names the SREV-322 boundary:
the first WerFault is resumed for WER/LocalDumps capture and later ones are
terminated only after the exact duplicate gate. The duplicate path no longer
calls `CloseHandle` on the caller-facing `PROCESS_INFORMATION` process/thread
handles while returning through the successful create path.

No predicate, duplicate-state flag, `ResumeThread`, `TerminateProcess`,
`WaitForSingleObject`, logging, return value, or output handle writeback behavior
changed.

## Acceptance Gate

`docs/plan/check-srev-322.py` validates the draft-07 schema, official Microsoft
references, source comment, WerFault predicate, first-WerFault resume/wait path,
repeated-WerFault terminate/wait path, duplicate-path premature handle close
removal, stale design-flaw wording removal, SREV-156/SREV-237 dump adjacency,
and split ledger fragment.

Windows gate: run the runtime verification matrix above before release. It must
prove first-WerFault dump capture, duplicate-WerFault suppression, duplicate
process handle remains caller-visible, caller-observable process/thread handle
behavior, WER configuration, dump output semantics, first/duplicate WerFault
process lifetime, handle readback, and in-process `EnableMiniDump` adjacency.

## Shared Runtime Capture Evidence

This SREV shares a user-mode lifecycle runtime evidence contract with SREV-092:

```text
docs/plan/srev-092-322-user-lifecycle-runtime-capture-playbook.md
docs/plan/srev-092-322-user-lifecycle-runtime-capture.schema.json
docs/plan/check-srev-092-322-user-lifecycle-runtime-capture.sh
```

The machine feature path for this entry is `werfault-localdumps-boundary`.

Windows gate: validate captured WerFault lifecycle records against
`docs/plan/srev-092-322-user-lifecycle-runtime-capture.schema.json` before any
duplicate-suppression, return, or process/thread handle writeback behavior
change.
