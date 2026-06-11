---
kind: srev-ledger-entry
id: SREV-253
title: Callsvc AppContainer DACL Boundary
status: patched-comment-topology-after-srev-081-appcontainer-port-dacl-review-no-behavior-change
owner: Sandboxie/core/dll/callsvc.c
spec: docs/plan/srev-253-callsvc-appcontainer-dacl-boundary.md
schema: docs/plan/srev-253-callsvc-appcontainer-dacl-boundary.schema.json
checker: docs/plan/check-srev-253.py
runtime_gate: Inherited from SREV-081 normal sandbox and AppContainer clients need Windows service-port connection proof
---

### SREV-253: Callsvc AppContainer DACL Boundary

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | patched comment/topology after SREV-081 AppContainer port DACL review; no behavior change |
| Evidence | SREV-081 already moved the AppContainer service-port access fix to the service owner: `Sandboxie/core/svc/PipeServer.cpp` `PipeServer::Start` publishes the SbieSvc port with explicit `WD` plus `AC` SDDL. `callsvc.c` still had a stale inline todo saying to make the service available for AppContainer processes. At this point the client-side condition is only a logging policy: AppContainer connect failures skip noisy `2203` client logs while SREV-081's Windows runtime proof remains open. |
| Data | `SbieDll_CallServer`, `SbieDll_ConnectPort`, `NtConnectPort`, `Dll_AppContainerToken`, `Silent`, `SbieApi_Log(2203)`, `PipeServer::Start`, `ConvertStringSecurityDescriptorToSecurityDescriptor`, `O:SYG:SYD:(A;;GA;;;WD)(A;;GA;;;AC)`, `WD`, `AC`, and SREV-081 runtime gate. |
| Schema | `CALLSVC_APPCONTAINER_DACL_BOUNDARY` says service-port access is owned by `PipeServer::Start`, not by client-side token bypass in `callsvc.c`; AppContainer reachability depends on the service port DACL carrying the AppContainer side of the access check; `callsvc.c` may suppress noisy connection logs for AppContainer callers while runtime proof remains open; `callsvc.c` must not impersonate, revert, or otherwise bypass AppContainer token semantics to connect; SREV-081 remains the behavior owner for the service-port DACL and Windows runtime proof; this SREV does not change `NtConnectPort`, request/reply chunking, service message IDs, or logging for ordinary non-silent clients. |
| Topology | Client path is `SbieDll_CallServer -> SbieDll_ConnectPort -> NtConnectPort("\\RPC Control\\SbieSvcPort") -> on failure, log only non-AppContainer and non-silent failures`. Service owner path is `PipeServer::Start -> explicit WD + AC service port DACL -> NtCreatePort -> AppContainer connection proof remains Windows runtime-gated`. |
| Logic Risk | The stale todo made the remaining client-side log predicate look like the owner of AppContainer availability. That is the wrong layer. The official shape and SREV-081 fix put access at the named service port security descriptor. A future agent following the stale todo could try to bypass AppContainer token semantics around `NtConnectPort`, which would contradict SREV-081's owner boundary. |
| Official Shape | `docs/plan/srev-253-callsvc-appcontainer-dacl-boundary.md` records Microsoft AppContainer, AppContainer named-object path, SDDL SID string, null-DACL, and DACL guidance references. `docs/plan/srev-253-callsvc-appcontainer-dacl-boundary.schema.json` records the JSON Schema draft-07 local `CALLSVC_APPCONTAINER_DACL_BOUNDARY` contract. |
| Fix | Comment-only source clarification. `callsvc.c` now says AppContainer service port access is owned by PipeServer's DACL and the client log suppression remains while SREV-081 is runtime-gated. No connect behavior, AppContainer token handling, silent-message list, request/reply chunking, or ordinary failure logging changed. |
| Acceptance Gate | `docs/plan/check-srev-253.py` validates the draft-07 schema, official reference links, SREV-081 adjacency, `PipeServer.cpp` explicit `WD` plus `AC` DACL shape, the new `callsvc.c` comment, removal of the stale todo text, unchanged `Dll_AppContainerToken && Silent` logging predicate, and the ledger fragment; `docs/plan/check-srev-253.sh` is the targeted wrapper. Runtime gate is inherited from SREV-081: normal sandbox clients and AppContainer sandbox clients still need Windows service-port connection proof. |
