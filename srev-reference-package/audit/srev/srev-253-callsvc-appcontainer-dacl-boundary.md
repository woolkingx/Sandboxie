# SREV-253: Callsvc AppContainer DACL Boundary

## Stage Gate

| Field | Value |
|---|---|
| Stage | schema -> topology -> logic -> action -> verify |
| Input artifact | `Sandboxie/core/dll/callsvc.c`, `Sandboxie/core/svc/PipeServer.cpp`, SREV-081, Microsoft AppContainer / SDDL / DACL references |
| Output artifact | `docs/plan/srev-253-callsvc-appcontainer-dacl-boundary.schema.json`, `docs/plan/check-srev-253.py`, `docs/plan/check-srev-253.sh`, ledger fragment, comment-only source clarification |
| Owner | Client-side service connect logging boundary for AppContainer callers |
| Acceptance gate | targeted source checker plus SREV-081 compatibility checker, core coverage, and diff checkpoint |

## Evidence

SREV-081 already moved the AppContainer service-port access fix to the service
owner:

```text
PipeServer::Start
  -> explicit SDDL DACL O:SYG:SYD:(A;;GA;;;WD)(A;;GA;;;AC)
  -> NtCreatePort("\\RPC Control\\SbieSvcPort")
  -> SbieDll_ConnectPort / NtConnectPort
```

`callsvc.c` still had a stale inline todo saying to make the service available
for AppContainer processes. At this point the client-side condition is only a
logging policy: AppContainer connect failures skip noisy `2203` client logs
while SREV-081's Windows runtime proof remains open.

Official references:

- https://learn.microsoft.com/en-us/windows/win32/secauthz/implementing-an-appcontainer
- https://learn.microsoft.com/en-us/windows/win32/api/securityappcontainer/nf-securityappcontainer-getappcontainernamedobjectpath
- https://learn.microsoft.com/en-us/windows/win32/secauthz/sid-strings
- https://learn.microsoft.com/en-us/windows/win32/secauthz/null-dacls-and-empty-dacls
- https://learn.microsoft.com/en-us/windows/win32/secbp/creating-a-dacl

## Data

`SbieDll_CallServer`, `SbieDll_ConnectPort`, `NtConnectPort`,
`Dll_AppContainerToken`, `Silent`, `SbieApi_Log(2203)`, `PipeServer::Start`,
`ConvertStringSecurityDescriptorToSecurityDescriptor`,
`O:SYG:SYD:(A;;GA;;;WD)(A;;GA;;;AC)`, `WD`, `AC`, and SREV-081 runtime gate.

## Schema

`CALLSVC_APPCONTAINER_DACL_BOUNDARY` says:

- service-port access is owned by `PipeServer::Start`, not by client-side token
  bypass in `callsvc.c`;
- AppContainer reachability depends on the service port DACL carrying the
  AppContainer side of the access check;
- `callsvc.c` may suppress noisy connection logs for AppContainer callers while
  runtime proof remains open;
- `callsvc.c` must not impersonate, revert, or otherwise bypass AppContainer
  token semantics to connect;
- SREV-081 remains the behavior owner for the service-port DACL and Windows
  runtime proof;
- this SREV does not change `NtConnectPort`, request/reply chunking, service
  message IDs, or logging for ordinary non-silent clients.

## Topology

Client path:

```text
SbieDll_CallServer
  -> SbieDll_ConnectPort
  -> NtConnectPort("\\RPC Control\\SbieSvcPort")
  -> on failure, log only non-AppContainer and non-silent failures
```

Service owner path:

```text
PipeServer::Start
  -> explicit WD + AC service port DACL
  -> NtCreatePort
  -> AppContainer connection proof remains Windows runtime-gated
```

## Logic Risk

The stale todo made the remaining client-side log predicate look like the owner
of AppContainer availability. That is the wrong layer. The official shape and
SREV-081 fix put access at the named service port security descriptor. A future
agent following the stale todo could try to bypass AppContainer token semantics
around `NtConnectPort`, which would contradict SREV-081's owner boundary.

## Fix

Comment-only source clarification. `callsvc.c` now says AppContainer service
port access is owned by PipeServer's DACL and the client log suppression remains
while SREV-081 is runtime-gated. No connect behavior, AppContainer token
handling, silent-message list, request/reply chunking, or ordinary failure
logging changed.

## Acceptance Gate

`docs/plan/check-srev-253.py` validates the draft-07 schema, official reference
links, SREV-081 adjacency, `PipeServer.cpp` explicit `WD` plus `AC` DACL shape,
the new `callsvc.c` comment, removal of the stale todo text, unchanged
`Dll_AppContainerToken && Silent` logging predicate, and the ledger fragment.

Runtime gate: inherited from SREV-081. Normal sandbox clients and AppContainer
sandbox clients still need Windows service-port connection proof.
