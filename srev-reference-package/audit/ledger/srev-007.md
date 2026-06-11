---
kind: srev-ledger-entry
id: SREV-007
title: Service Start Broker Relies On SCM ACL Instead Of Sandboxie Policy Gate
status: patched-comment-policy-classification-after-official-scm-access-review-no-behavior-change
owner: "Sandboxie/core/svc/serviceserver.cpp:99-107"
spec: docs/plan/srev-007-service-start-policy-spec.md
schema: docs/plan/srev-007-service-start-policy-spec.schema.json
checker: docs/plan/check-srev-007.sh
runtime_gate: "a sandboxed non-admin caller without `SERVICE_START` on the host service receives `ERROR_ACCESS_DENIED`; if Sandboxie chooses stricter-than-SCM policy, the new rule is explicit and runtime-tested"
---
### SREV-007: Service Start Broker Relies On SCM ACL Instead Of Sandboxie Policy Gate

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched comment/policy classification after official SCM access review; no behavior change |
| Evidence | Explorer Newton reported `Sandboxie/core/svc/serviceserver.cpp:99-107` had a source comment saying an admin check should be performed, while the handler validates the request range and then calls `OpenService(..., SERVICE_START)` / `StartService` at `serviceserver.cpp:115-123`. Microsoft documents SCM/service access checks through the caller token and service security descriptor. Locally, `ServiceServer::Handler` calls `PipeServer::ImpersonateCaller(&msg)` before dispatching `MSGID_SERVICE_START`. |
| Data | `SERVICE_START_REQ` with requested service name. |
| Schema | `SERVICE_START_POLICY_POSTURE` says `OpenSCManager` checks the caller token against the SCM security descriptor, `OpenServiceW` grants service object access based on the service security descriptor, `StartServiceW` requires `SERVICE_START`, `StartHandler` runs under the impersonated caller token, and no code change should replace SCM DACL semantics with admin-only or elevation-style checks without compatibility evidence. |
| Topology | Sandboxed client request crosses into host Service Control Manager through SbieSvc. |
| Logic Risk | The old comment made an unproven admin-only/elevation check look like the expected repair. That would silently replace SCM DACL semantics and could break legitimate non-admin service-start grants. |
| Official Shape | `docs/plan/srev-007-service-start-policy-spec.md` records Microsoft SCM/service access-right semantics and the local `ImpersonateCaller -> SCM` topology. |
| Fix | Comment-only policy clarification. The source now names SREV-007 and states that, because the handler impersonates the caller before dispatch, the host service object's SCM DACL is the current authorization owner through `OpenService(..., SERVICE_START)`. It rejects blind admin-only/elevation gates unless Sandboxie first defines a stricter explicit policy owner such as an allowlist. No service name validation, impersonation, `OpenSCManager`, `OpenService`, `StartService`, or reply behavior changed. |
| Acceptance Gate | `docs/plan/check-srev-007.sh` proves service-start dispatch still impersonates the caller, validates the service name before SCM, documents SCM DACL delegation in source, removes the stale admin/elevation repair comment, preserves official SCM access references, and keeps the Windows runtime gate visible. Windows gate: a sandboxed non-admin caller without `SERVICE_START` on the host service receives `ERROR_ACCESS_DENIED`; if Sandboxie chooses stricter-than-SCM policy, the new rule is explicit and runtime-tested. |
