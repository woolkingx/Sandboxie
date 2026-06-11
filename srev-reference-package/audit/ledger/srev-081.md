---
kind: srev-ledger-entry
id: SREV-081
title: PipeServer AppContainer Port DACL
status: patched-source-level-after-official-appcontainer-dual-principal-and-named-object
owner: Sandboxie/core/dll/callsvc.c
spec: docs/plan/srev-081-pipeserver-appcontainer-port-dacl.md
schema: docs/plan/srev-081-pipeserver-appcontainer-port-dacl.schema.json
checker: docs/plan/check-srev-081.py
runtime_gate: "normal sandbox clients still connect to the SbieSvc port; AppContainer sandbox clients can connect when the OS supports the All AppContainers SID; older OS builds that do not recognize `AC` still start with the explicit legacy `WD` DACL"
---
### SREV-081: PipeServer AppContainer Port DACL

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official AppContainer dual-principal and named-object security descriptor shape; needs Windows AppContainer service-port runtime proof |
| Evidence | `Sandboxie/core/dll/callsvc.c` used to say service availability for AppContainer processes still needed fixing. The client call path opens `\\RPC Control\\SbieSvcPort` with `NtConnectPort`; the service owner is `Sandboxie/core/svc/PipeServer.cpp`, which created the named LPC port with a NULL DACL because the local comment wanted any process to connect. Microsoft documents that AppContainer access has a package/capability SID half in addition to normal user/group SIDs, and its named-object example grants All AppContainers explicitly. Microsoft also documents `AC` as the SDDL SID alias for All App Packages and warns that NULL DACLs grant all access. |
| Data | SbieSvc named LPC port, service port security descriptor, AppContainer token package/capability SID half, regular user/group SID half, `NtConnectPort` result, and `SbieDll_CallServer` request/reply protocol. |
| Schema | `PIPESERVER_APPCONTAINER_PORT_DACL` says the service side owns the named port security descriptor; clients must not bypass AppContainer token semantics; ordinary clients keep the legacy any-process connect shape through `WD`; AppContainer clients need an explicit `AC` ACE on systems that understand `AC`; older systems fall back to an explicit `WD` DACL; the port must not be published with a NULL DACL. |
| Topology | `PipeServer::Start` constructs the port security descriptor, calls `NtCreatePort`, and publishes the named service port consumed by `SbieDll_ConnectPort` / `SbieDll_CallServer`. The access fix belongs at this service-owned boundary, not in `callsvc.c` token switching. |
| Logic Risk | A NULL DACL is an implicit no-access-control shape, not the official AppContainer named-object access shape. It also hides the real owner boundary: the client-side TODO should be solved by making the service port's ACL represent both the normal and AppContainer principals, rather than by bypassing caller identity during connect. |
| Official Shape | `docs/plan/srev-081-pipeserver-appcontainer-port-dacl.md` records Microsoft AppContainer, `GetAppContainerNamedObjectPath`, SDDL SID string, null-DACL, and DACL guidance references. `docs/plan/srev-081-pipeserver-appcontainer-port-dacl.schema.json` records the JSON Schema draft-07 local `PIPESERVER_APPCONTAINER_PORT_DACL` contract. |
| Fix | `PipeServer::Start` now creates the named service port with explicit SDDL `O:SYG:SYD:(A;;GA;;;WD)(A;;GA;;;AC)`, preserving ordinary client reachability through `WD` and adding the AppContainer `AC` principal. If the OS does not recognize `AC`, it falls back to explicit `O:SYG:SYD:(A;;GA;;;WD)`. The allocated security descriptor is released with `LocalFree` after `NtCreatePort`. |
| Acceptance Gate | `docs/plan/check-srev-081.py` validates the draft-07 schema, official references, `PipeServer.cpp` SDDL include, explicit `WD` plus `AC` DACL, legacy fallback DACL, `LocalFree` ownership, stale NULL-DACL removal, client-side comment routing to the service-owned DACL boundary, and ledger entry; `docs/plan/check-srev-081.sh` is the matrix wrapper. Windows gate: normal sandbox clients still connect to the SbieSvc port; AppContainer sandbox clients can connect when the OS supports the All AppContainers SID; older OS builds that do not recognize `AC` still start with the explicit legacy `WD` DACL. |
