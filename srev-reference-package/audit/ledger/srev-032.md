---
kind: srev-ledger-entry
id: SREV-032
title: SuspendOne Process Handle Shape
status: patched-source-level-after-official-openprocess-closehandle-contract-analysis-ne
owner: "Sandboxie/core/svc/ProcessServer.cpp:2253-2260"
spec: docs/plan/srev-032-process-suspend-one.md
schema: docs/plan/srev-032-process-suspend-one.schema.json
checker: docs/plan/check-srev-032.py
runtime_gate: "authorized suspend/resume succeeds for a valid sandboxed process, while a raced/denied target open returns `STATUS_INVALID_CID` without using or closing an invalid handle"
---
### SREV-032: SuspendOne Process Handle Shape

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official OpenProcess/CloseHandle contract analysis; needs Windows suspend/resume race proof |
| Evidence | `Sandboxie/core/svc/ProcessServer.cpp:2253-2260` opened the target process with `OpenProcess(PROCESS_SUSPEND_RESUME, ...)`, then passed `hProcess` to `NtSuspendProcess` / `NtResumeProcess` and `CloseHandle` without proving that `OpenProcess` succeeded. The sibling `SuspendAllHandler` already gates the same native calls with `if (hProcess)`. |
| Data | `PROCESS_SUSPEND_RESUME_ONE_REQ` carries a target PID and a suspend/resume boolean. The SbieSvc handler owns the opened process handle. |
| Schema | `OpenProcess` returns `NULL` on failure and an open process handle on success. `CloseHandle` requires a valid open handle. Native suspend/resume must receive only the successfully opened process handle. |
| Topology | Unsandboxed caller request crosses SbieSvc authorization, target process identity/box/session checks, then enters the Win32 process-handle boundary before native suspend/resume. |
| Logic Risk | If the target exits, access is denied, or `OpenProcess` otherwise fails after earlier process identity checks, the handler can pass `NULL` to native suspend/resume and then close an invalid handle. |
| Official Shape | `docs/plan/srev-032-process-suspend-one.md` records Microsoft `OpenProcess`, `CloseHandle`, and NTSTATUS status-shape references. `docs/plan/srev-032-process-suspend-one.schema.json` records the small local wire/handle schema. |
| Fix | `SuspendOneHandler` now returns `STATUS_INVALID_CID` immediately when `OpenProcess(PROCESS_SUSPEND_RESUME, ...)` returns `NULL`; native suspend/resume and `CloseHandle` run only on the success path. |
| Acceptance Gate | `docs/plan/check-srev-032.py` validates the schema and source handle order; `docs/plan/check-srev-032.sh` is the matrix wrapper. Windows gate: authorized suspend/resume succeeds for a valid sandboxed process, while a raced/denied target open returns `STATUS_INVALID_CID` without using or closing an invalid handle. |
