---
kind: srev-ledger-entry
id: SREV-009
title: Session-0 Process Launch Token Is Nullified Before CreateProcessAsUser
status: patched-source-level-after-official-token-api-shape-needs-windows-session-0-runt
owner: "Sandboxie/core/svc/ProcessServer.cpp:1306-1328"
spec: docs/plan/srev-009-session0-token-spec.md
schema: docs/plan/srev-009-session0-token-spec.schema.json
checker: docs/plan/check-srev-009.sh
runtime_gate: runtime smoke proves intended token/session for StartSystemBox/session-0 launch
---
### SREV-009: Session-0 Process Launch Token Is Nullified Before CreateProcessAsUser

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official token/API shape; needs Windows session-0 runtime proof |
| Evidence | Explorer Newton reports `Sandboxie/core/svc/ProcessServer.cpp:1306-1328`: code opens/duplicates a token, then closes and nulls `PrimaryTokenHandle` before passing it to `CreateProcessAsUser`. |
| Data | Primary token handle for Session 0 / StartSystemBox launch path. |
| Schema | `CreateProcessAsUserW` has a documented token parameter and required access rights; NULL-token behavior must be verified before relying on it. |
| Topology | Service process launch broker chooses host/service token for process creation. |
| Logic Risk | Comment and code disagree about which token owns the launch; a NULL token can shift behavior to implicit caller context and drift across Windows versions. |
| Official Shape | `docs/plan/srev-009-session0-token-spec.md` records `CreateProcessAsUserW` primary-token requirements and `DuplicateToken` / `DuplicateTokenEx` token-type semantics. |
| Fix | Session-0 launch now keeps SbieSvc's own primary token alive through `CreateProcessAsUser`, uses a separate impersonation-token duplicate for thread impersonation, preserves `GetLastError` on token-open/duplicate failure, and closes the temporary session-0 primary token before returning. |
| Acceptance Gate | `docs/plan/check-srev-009.sh` proves the selected session-0 primary token is assigned before `CreateProcessAsUser` and closed only after the create path. Windows gate: runtime smoke proves intended token/session for StartSystemBox/session-0 launch. |
