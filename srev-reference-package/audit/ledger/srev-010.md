---
kind: srev-ledger-entry
id: SREV-010
title: Sandboxie UAC Broker Waits Forever On Helper Process
status: patched-source-level-after-official-wait-process-semantics-and-local-helper-topo
owner: "Sandboxie/core/svc/serviceserver2.cpp:568"
spec: docs/plan/srev-010-uac-helper-wait.md
schema: docs/plan/srev-010-uac-helper-wait.schema.json
checker: docs/plan/check-srev-010.sh
runtime_gate: "hung prompt helper does not pin an SbieSvc worker; normal `IDYES` and `IDNO` prompt exits preserve current behavior"
---
### SREV-010: Sandboxie UAC Broker Waits Forever On Helper Process

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | patched source-level after official wait/process semantics and local helper topology analysis; needs Windows hung-helper runtime proof |
| Evidence | Explorer Newton reports `Sandboxie/core/svc/serviceserver2.cpp:568` waits `INFINITE` for the UAC helper process. |
| Data | `SERVICE_UAC_REQ` and helper process handle. |
| Schema | Broker helper lifetime must be bounded or tied to caller/process lifetime. |
| Topology | SbieSvc worker thread crosses into GUI/UAC helper process. |
| Logic Risk | A stuck helper can pin a service worker indefinitely. |
| Official Shape | `docs/plan/srev-010-uac-helper-wait.md` records Microsoft `WaitForSingleObject`, process-signaling, and termination posture. |
| Fix | The dedicated `Start.exe uac_prompt` helper wait is now bounded by `SBIE_UAC_PROMPT_TIMEOUT_MS`. Timeout terminates that dedicated helper, sets `ERROR_TIMEOUT`, and falls through to the existing fail-closed `RunUacSlave3(..., JustFail=true, ...)` path. |
| Acceptance Gate | `docs/plan/check-srev-010.sh` proves the `uac_prompt` helper no longer waits forever and timeout reaches the existing JustFail path. Windows gate: hung prompt helper does not pin an SbieSvc worker; normal `IDYES` and `IDNO` prompt exits preserve current behavior. |
