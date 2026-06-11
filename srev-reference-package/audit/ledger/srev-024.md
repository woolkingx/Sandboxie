---
kind: srev-ledger-entry
id: SREV-024
title: KillAll Uses Uninitialized Job Mode And Reads Past PID Count
status: patched-source-level-after-official-job-process-termination-and-local-enum-count
owner: "Sandboxie/core/svc/ProcessServer.cpp:255-292"
spec: docs/plan/srev-024-killall-enum-count.md
schema: docs/plan/srev-024-killall-enum-count.schema.json
checker: docs/plan/check-srev-024.sh
runtime_gate: "job-disabled KillAll never sends `GUI_KILL_JOB`; manual fallback terminates exactly the returned PIDs; job-enabled boxes still run job kill before fallback; boxed RPCSS caller still avoids job termination"
---
### SREV-024: KillAll Uses Uninitialized Job Mode And Reads Past PID Count

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official job/process termination and local enum-count analysis; needs Windows KillAll runtime proof |
| Evidence | `Sandboxie/core/svc/ProcessServer.cpp:255-292` declared `TerminateJob` without a default and only assigned it on selected branches; `ProcessServer.cpp:348-370` iterated `for (i = 0; i <= count; ++i)` after `SbieApi_EnumProcessEx` returned the number of PIDs written. |
| Data | `PROCESS_KILL_ALL_REQ`, `TerminateJob` mode bit, and local `pids[512]` output array. |
| Schema | `SbieApi_EnumProcessEx` returns `count` as the number of valid PID entries, so valid indexes are `0 <= i < count`. Job termination mode must be deterministic and policy-selected. |
| Topology | Service broker receives kill-all request, optionally asks GUI slave to terminate the sandbox job object, then manually terminates enumerated sandbox processes as fallback. |
| Logic Risk | Uninitialized `TerminateJob` can randomly select job termination when config disables it; the manual fallback can read and terminate a stale `pids[count]` value outside the returned PID slice. |
| Official Shape | `docs/plan/srev-024-killall-enum-count.md` records Microsoft `TerminateJobObject` and `TerminateProcess` executor semantics plus the local Sandboxie PID enumeration contract. |
| Fix | `TerminateJob` now defaults through `TerminateJob = FALSE` and only becomes true through the explicit `TerminateJobObject` policy branch. `KillAllHelper` now loops with `i < count`. |
| Acceptance Gate | `docs/plan/check-srev-024.sh` proves job mode has a default false value and the PID loop no longer reads `pids[count]`. Windows gate: job-disabled KillAll never sends `GUI_KILL_JOB`; manual fallback terminates exactly the returned PIDs; job-enabled boxes still run job kill before fallback; boxed RPCSS caller still avoids job termination. |
