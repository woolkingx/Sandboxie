# SREV-262: DLL Main PCA Restart Comment Owner

## Stage Gate

| Field | Value |
|---|---|
| Stage | schema -> topology -> logic -> action -> verify |
| Input artifact | `Sandboxie/core/dll/dllmain.c`, SREV-085 |
| Output artifact | `docs/plan/srev-262-dllmain-pca-restart-comment-owner.schema.json`, `docs/plan/check-srev-262.py`, `docs/plan/check-srev-262.sh`, ledger fragment, comment-only source clarification |
| Owner | `Dll_Init` PCA/AppContainer restart comment |
| Acceptance gate | targeted source checker plus SREV-085 adjacency checker, core coverage, and diff checkpoint |

## Evidence

SREV-085 already owns the PCA restart topology: process flags identify a process
already running in a PCA job, AppContainer processes skip that restart path, and
the replacement process is created through SbieSvc before Sandboxie job attach.

The remaining `dllmain.c` comment still described the path as a generic
workaround and repeated the AppContainer exclusion as a note. That wording did
not name the SREV owner or the service boundary that makes the restart legal.

## Data

`Dll_ProcessFlags`, `SBIE_FLAG_PROCESS_IN_PCA_JOB`,
`SBIE_FLAG_PROCESS_IN_APP_PKG`, `NoRestartOnPCA`, `MustRestartProcess`,
`SbieApi_MonitorPutMsg`, `Proc_RestartProcessOutOfPcaJob`, and SREV-085.

## Schema

`DLLMAIN_PCA_RESTART_COMMENT_OWNER` says:

- SREV-085 owns the PCA job restart topology;
- `dllmain.c` decides whether restart is needed before Sandboxie job attach;
- AppContainer processes skip this PCA restart path;
- this SREV does not change flags, policy reads, monitor output, service
  restart transport, command-line payload shape, or runtime behavior.

## Topology

```text
SREV-085 PCA restart owner
  -> dllmain process-flag restart decision
  -> Proc_RestartProcessOutOfPcaJob
  -> SbieSvc replacement process
  -> Sandboxie job attach
```

## Logic Risk

Generic workaround comments hide the owner boundary. The PCA path is not an
isolated local trick; it depends on the official job-object topology already
recorded by SREV-085 and on SbieSvc owning creation of the replacement process.
Future changes must preserve or reprove that boundary.

## Fix

Comment-only source clarification. The source now says SREV-085 owns the PCA
job restart topology, that already-jobbed processes are replaced through SbieSvc
before Sandboxie job attach, and that AppContainer processes skip this restart
path. No behavior changed.

## Acceptance Gate

`docs/plan/check-srev-262.py` validates the draft-07 schema, source comment,
unchanged PCA/AppContainer decision terms, SREV-085 adjacency, and the ledger
fragment.

Runtime gate: inherited from SREV-085.
