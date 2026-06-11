# SREV-092 / SREV-322: User-Mode Lifecycle Runtime Capture Playbook

## Stage Gate

| Field | Value |
|---|---|
| Stage | schema |
| Input artifact | SREV-092, SREV-322, `Sandboxie/core/dll/scm_msi.c`, `Sandboxie/core/dll/proc.c`, Microsoft loader notification / MSI handle / event / WER LocalDumps / process-lifetime documentation |
| Output artifact | `docs/plan/srev-092-322-user-lifecycle-runtime-capture.schema.json`, `docs/plan/check-srev-092-322-user-lifecycle-runtime-capture.py`, runtime capture checklist |
| Owner | user-mode lifecycle evidence contract for MSI last-user event ownership and WerFault LocalDumps suppression |
| Acceptance gate | targeted checker validates source/spec adjacency and the evidence schema; Windows capture remains the runtime gate |

## Official Surface

SREV-092 and SREV-322 share a lifecycle rule: a process or handle event is not a
semantic owner until runtime evidence proves it is the right edge in the Windows
topology.

For MSI, Microsoft documents loader notifications as load/unload observations,
not as a safe callback surface for arbitrary module work. Microsoft documents
`MsiCloseHandle` as closing one installer handle from the same creating thread,
and `MsiCloseAllHandles` as diagnostic rather than cleanup ownership. The named
event is destroyed when its last handle is closed, so Sandboxie must prove the
last real MSI user before releasing the event that keeps sandboxed MSIServer
alive.

For WerFault, Microsoft documents WER LocalDumps as registry-controlled dump
capture after a crash. Dump output depends on LocalDumps keys, dump folder ACL,
DumpCount, DumpType, WER state, and automatic-debugger state. `TerminateProcess`
is unconditional and asynchronous for another process, and `CloseHandle` only
closes the caller's handle. Therefore duplicate WerFault suppression must prove
dump output and caller-visible handle semantics, not just process termination.

Official references:

```text
https://learn.microsoft.com/en-us/windows/win32/devnotes/ldrregisterdllnotification
https://learn.microsoft.com/en-us/windows/win32/devnotes/ldrdllnotification
https://learn.microsoft.com/en-us/windows/win32/api/msi/nf-msi-msiclosehandle
https://learn.microsoft.com/en-us/windows/win32/api/msi/nf-msi-msicloseallhandles
https://learn.microsoft.com/en-us/windows/win32/sync/event-objects
https://learn.microsoft.com/en-us/windows-hardware/drivers/debugger/windows-error-reporting
https://learn.microsoft.com/en-us/windows/win32/wer/collecting-user-mode-dumps
https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-resumethread
https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-terminateprocess
https://learn.microsoft.com/en-us/windows/win32/api/synchapi/nf-synchapi-waitforsingleobject
https://learn.microsoft.com/en-us/windows/win32/api/handleapi/nf-handleapi-closehandle
```

Legal route:

```text
official lifecycle/API shape -> Windows runtime capture -> local lifecycle owner decision
```

Illegal route:

```text
one handle closed or one dump exists -> last-owner and caller-visible semantics are proven
```

## Data

Each capture record must identify shared runtime coordinates:

- Windows build, architecture, Sandboxie commit, box name, process image,
  capture tool, timestamp, and test case id.
- Feature path: `msi-last-user-event` for SREV-092 or
  `werfault-localdumps-boundary` for SREV-322.
- Machine key: `feature path: `msi-last-user-event``.
- Machine key: `feature path: `werfault-localdumps-boundary``.
- Route result: `msi-event-held`, `msi-event-released`, `msi-server-exited`,
  `msi-server-kept-alive`, `werfault-first-resumed`, `werfault-duplicate-terminated`,
  `werfault-nonmatch-resumed`, `negative-control-passed`, or `combined`.
- Evidence coordinates: event trace, process trace, loader trace, MSI API trace,
  WER dump folder snapshot, Sandboxie log, caller handle readback, and notes.

SREV-092 MSI records must include:

- MSI entry path: install, repair, uninstall, advertised repair, custom action,
  or negative control.
- Client shape: one client process, multiple concurrent clients, nested custom
  action, early client crash, or non-MSI process.
- Module lifecycle: `msi.dll` load/unload notification, `Ldr_MyDllCallbackNew`
  load/unload state, and whether `Scm_MsiDll` was called.
- Event lifecycle: `CreateEvent(SBIE_WindowsInstallerInUse)`, client event
  handle open/close, MSI server `OpenEvent` success/failure, and
  `CloseHandle(Msi_ServerInUseEvent)`.
- MSI handle lifecycle: `MsiOpenPackage`, `MsiOpenProduct`,
  `MsiGetActiveDatabase`, `MsiDatabaseOpenView`, `MsiViewFetch`,
  `MsiCloseHandle`, cross-thread handle owner, and `MsiCloseAllHandles`
  diagnostic count.
- MSIServer lifecycle: sandboxed MSIServer start, waiter polling, last-user
  exit, and non-exit while custom actions or installer handles remain active.

SREV-322 WerFault records must include:

- WER configuration: global/per-application LocalDumps, DumpFolder, DumpCount,
  DumpType, CustomDumpFlags, folder ACL, WER disabled, automatic debugger, and
  missing-key controls.
- Sandbox configuration: `EnableMiniDump=y`, `EnableMiniDump=n`, default box,
  restricted token box, and blocked write access to dump folder.
- Crash source: deterministic native crash, repeated crash in same box, custom
  crash reporter, non-crashing child, and WerFault outside exact predicate.
- WerFault path: first/duplicate process ids, exact predicate match,
  `ResumeThread` result, `TerminateProcess` result, wait result, exit code,
  `SbieApi_Log(2224)`, and duplicate-state flag.
- Dump output: dump path, count, timestamp order, dump type, process identity,
  DumpCount replacement behavior, and no-dump readback under disabled/denied
  controls.
- Handle semantics: caller-visible `PROCESS_INFORMATION` process/thread handle
  validity, `GetExitCodeProcess`, `WaitForSingleObject`, and `CloseHandle`
  readback for first, duplicate, non-WerFault, and failure paths.

## Schema

Machine-readable capture records use:

```text
docs/plan/srev-092-322-user-lifecycle-runtime-capture.schema.json
```

The schema accepts one record per runtime observation. A record can carry an MSI
lifecycle payload, a WerFault lifecycle payload, or both when one scenario
captures both process families.

## Topology

SREV-092:

```text
msi.dll load
  -> Sandboxie loader callback
  -> Scm_MsiDll
  -> named event keeps sandboxed MSIServer alive
  -> true last MSI user closes final event handle
  -> MSIServer waiter observes OpenEvent failure and exits
```

Forbidden shortcut:

```text
MsiCloseHandle(one handle) -x-> proven last MSI user
```

SREV-322:

```text
created suspended WerFault
  -> first WerFault: ResumeThread -> WER LocalDumps capture -> wait/readback
  -> duplicate WerFault: TerminateProcess -> wait/readback -> handle semantics
```

Forbidden shortcut:

```text
dump file exists -x-> duplicate suppression and PROCESS_INFORMATION semantics proven
```

## Required Captures

SREV-092 positive and negative controls:

| Capture | Expected Proof |
|---|---|
| One MSI client with successful install/repair/uninstall | Event is held while the client uses MSI and MSIServer exits after the last real user |
| Multiple concurrent MSI clients | Closing one client's event or handle does not exit MSIServer early |
| Nested custom action | MSIServer remains alive while custom action still owns MSI work |
| Early client crash | Waiter eventually exits only after the named event truly disappears |
| Per-thread `MsiCloseHandle` | Closing one handle is not treated as last-user ownership |
| `MsiCloseAllHandles` diagnostic count | Diagnostic readback is not cleanup ownership |
| Non-MSI DLL churn | Loader unload noise does not release the MSI in-use event |

SREV-322 positive and negative controls:

| Capture | Expected Proof |
|---|---|
| Fresh-box first WerFault | First path resumes, WER writes expected dump, and caller handle readback is valid |
| Repeated crash in same box | Duplicate WerFault is terminated and caller-visible handle semantics are recorded |
| `EnableMiniDump` on/off | Sandboxie in-process dumps remain independent of WER LocalDumps |
| WER disabled / LocalDumps missing | Normal process creation is preserved and no-dump state is correctly classified |
| Automatic debugger configured | LocalDumps suppression follows Microsoft-documented owner, not Sandboxie duplicate logic |
| Dump folder ACL denied | No dump output is attributed to ACL denial, not to successful process-lifetime policy |
| Non-WerFault child / WerFault outside predicate | Normal resume path is not duplicate-suppressed |

## Logic Risk

SREV-092 can exit MSIServer early if Sandboxie treats a per-handle or per-thread
MSI event as the last real MSI user. SREV-322 can hide caller-visible handle
breakage if duplicate WerFault suppression closes handles while still reporting
successful process creation. In both cases, the right owner is an observed
Windows lifecycle edge, not a convenient local hook point.

## Acceptance Gate

Linux/source gate:

```bash
bash docs/plan/check-srev-092-322-user-lifecycle-runtime-capture.sh
bash docs/plan/check-srev-092.sh
bash docs/plan/check-srev-322.sh
```

Windows gate:

1. Build Sandboxie DLLs for each target architecture.
2. Capture SREV-092 MSI lifecycle observations across client, handle, custom
   action, crash, and MSIServer waiter controls.
3. Capture SREV-322 WerFault LocalDumps observations across WER settings, crash
   paths, duplicate suppression, handle readback, and EnableMiniDump adjacency.
4. Store one JSON record per build/architecture/process/control.
5. Validate records against
   `docs/plan/srev-092-322-user-lifecycle-runtime-capture.schema.json`.
6. Only after records validate may MSI event-release behavior or WerFault
   return/handle-writeback behavior change.
