---
kind: srev-ledger-entry
id: SREV-065
title: SCM Sppsvc Handle Lifetime
status: patched-source-level-after-official-scm-handle-lifetime-shape-and-local-scm-star
owner: Sandboxie/core/dll/scm_misc.c
spec: docs/plan/srev-065-scm-sppsvc-handle-lifetime.md
schema: docs/plan/srev-065-scm-sppsvc-handle-lifetime.schema.json
checker: docs/plan/check-srev-065.py
runtime_gate: "`sppsvc` already-running path, stopped-and-startable path, open-service failure, start/query failure, and handle-count stability across repeated calls"
---
### SREV-065: SCM Sppsvc Handle Lifetime

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official SCM handle lifetime shape and local `Scm_Start_Sppsvc` ownership analysis; needs Windows service-start runtime proof |
| Evidence | `Sandboxie/core/dll/scm_misc.c` `Scm_Start_Sppsvc` opens the SCM with `Scm_OpenSCManagerW`, declares an outer `handle2 = NULL`, then previously declared another inner `SC_HANDLE handle2` for the `Scm_OpenServiceWImpl` result. Microsoft documents handles from `OpenSCManagerW` and `OpenServiceW` as SCM/service object handles closed by `CloseServiceHandle`. Because the inner service handle shadowed the outer cleanup slot, the final cleanup block closed the SCM handle but skipped the opened service handle. |
| Data | SCM handle from `Scm_OpenSCManagerW`, `sppsvc` service handle from `Scm_OpenServiceWImpl`, service start/polling path, and `Scm_CloseServiceHandleImpl` cleanup edge. |
| Schema | `SCM_SPPSVC_HANDLE_LIFETIME` says `Scm_Start_Sppsvc` owns both `handle1` and `handle2` until cleanup; the service-open result must be assigned to the outer `handle2` lifetime slot and must not be shadowed by a nested declaration. |
| Topology | `OpenSCManager` flows into SCM handle ownership; `OpenService` flows into service handle ownership; both handles must flow to the function cleanup block unless ownership is explicitly transferred, which it is not. |
| Logic Risk | A service-start helper that leaks a service handle on every successful open can accumulate process handle leaks in compatibility paths triggered from RPC binding composition. Shadowing also hides lifetime from later reviewers because the cleanup block appears present but cannot see the opened service handle. |
| Official Shape | `docs/plan/srev-065-scm-sppsvc-handle-lifetime.md` records Microsoft `OpenSCManagerW`, `OpenServiceW`, and `CloseServiceHandle` references. `docs/plan/srev-065-scm-sppsvc-handle-lifetime.schema.json` records the JSON Schema draft-07 local `SCM_SPPSVC_HANDLE_LIFETIME` contract. |
| Fix | `Scm_Start_Sppsvc` now assigns the `Scm_OpenServiceWImpl` result to the outer `handle2` cleanup-owned variable. The existing cleanup block closes both `handle1` and `handle2` when present. |
| Acceptance Gate | `docs/plan/check-srev-065.py` validates the draft-07 schema, official references, outer service-handle assignment, absence of the nested `handle2` shadow, both close calls, and ledger entry; `docs/plan/check-srev-065.sh` is the matrix wrapper. Windows gate: `sppsvc` already-running path, stopped-and-startable path, open-service failure, start/query failure, and handle-count stability across repeated calls. |
