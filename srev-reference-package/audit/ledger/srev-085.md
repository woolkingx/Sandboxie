---
kind: srev-ledger-entry
id: SREV-085
title: PCA Restart Command-Line Shape
status: patched-source-level-after-official-job-object-getcommandlinew-createprocessw-an
owner: Sandboxie/core/dll/dllmain.c
spec: docs/plan/srev-085-pca-restart-command-line-shape.md
schema: docs/plan/srev-085-pca-restart-command-line-shape.schema.json
checker: docs/plan/check-srev-085.py
runtime_gate: a forced process launched from a PCA-job parent restarts through SbieSvc with short and long command lines, AppContainer processes skip the PCA restart path, and Digital Guardian module detection still drives the existing file/loader compatibility behavior
---
### SREV-085: PCA Restart Command-Line Shape

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official job-object, `GetCommandLineW`, `CreateProcessW`, and current-directory shape; needs Windows PCA restart runtime proof |
| Evidence | `Sandboxie/core/dll/dllmain.c` contains comment-admitted startup compatibility state for Digital Guardian and for Program Compatibility Assistant (PCA) job restart. Microsoft documents job objects as unbreakable process associations, child process job inheritance, pre-Windows-8 single-job limits, and nested-job hierarchy constraints. `dllmain.c` already gates PCA restart on `SBIE_FLAG_PROCESS_IN_PCA_JOB`, excludes `SBIE_FLAG_PROCESS_IN_APP_PKG`, and honors `NoRestartOnPCA`. The restart implementation in `Sandboxie/core/dll/proc.c` then copied `GetCommandLine()` into a fixed 8192-WCHAR buffer with `wcscpy`, even though Microsoft documents `GetCommandLineW` as returning system-owned variable-length input and the restart path forwards that command line into process creation. |
| Data | Digital Guardian module-presence flag, driver process flags, PCA-job state, AppContainer state, forced-process policy, system-owned command-line input, current-directory payload, and service-owned `RunSandboxed` process creation. |
| Schema | `PCA_RESTART_COMMAND_LINE_SHAPE` says PCA/job detection decides whether restart is needed before sandbox job attach; AppContainer processes do not use the PCA restart path; `GetCommandLine` returns system-owned read-only input; restart command-line storage is sized from the actual command-line length; the restart payload must not copy a variable-length command line into a fixed local buffer; Digital Guardian detection remains an early module-presence compatibility flag. |
| Topology | Driver flags flow into `dllmain.c`; `dllmain.c` decides whether the current process must be replaced; `Proc_RestartProcessOutOfPcaJob` builds the restart payload; `SbieDll_RunSandboxed` crosses to SbieSvc; `ProcessServer::RunSandboxedStartProcess` creates and attaches the replacement process. Digital Guardian state is detected in `dllmain.c` / `ldr.c` and consumed by `file.c` compatibility paths. |
| Logic Risk | Restarting out of a PCA job is compatible with the official job-object model, but the restart payload must preserve the official command-line shape. A fixed 8192-WCHAR `wcscpy` can corrupt the process before SbieSvc receives the restart request, turning a job-topology workaround into a local buffer-shape bug. The Digital Guardian comment-risk is classified as third-party module-presence compatibility state and is not changed by this patch. |
| Official Shape | `docs/plan/srev-085-pca-restart-command-line-shape.md` records Microsoft job object, nested jobs, `AssignProcessToJobObject`, `GetCommandLineW`, `CreateProcessW`, and `GetCurrentDirectory` references. `docs/plan/srev-085-pca-restart-command-line-shape.schema.json` records the JSON Schema draft-07 local `PCA_RESTART_COMMAND_LINE_SHAPE` contract. |
| Fix | `Proc_RestartProcessOutOfPcaJob` now measures the actual `GetCommandLine` string length, checks overflow against the local allocator byte-size boundary, allocates enough storage for the terminating NUL, and copies the system-owned input into the restart payload with `memcpy`. |
| Acceptance Gate | `docs/plan/check-srev-085.py` validates the draft-07 schema, official references, `dllmain.c` PCA/AppContainer restart gate and SREV-085 comment owner, Digital Guardian classification evidence, dynamic command-line allocation in `proc.c`, stale fixed command-line buffer removal, SREV-262 adjacency, and ledger entry; `docs/plan/check-srev-085.sh` is the targeted wrapper. Windows gate: a forced process launched from a PCA-job parent restarts through SbieSvc with short and long command lines, AppContainer processes skip the PCA restart path, and Digital Guardian module detection still drives the existing file/loader compatibility behavior. |
