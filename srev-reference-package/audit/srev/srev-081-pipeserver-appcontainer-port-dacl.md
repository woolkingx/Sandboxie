# SREV-081: PipeServer AppContainer Port DACL

## Data

`Sandboxie/core/dll/callsvc.c` used to record that service calls were not
available for AppContainer processes. The client connects to the service through
`SbieDll_ConnectPort`, which opens the named service port created by
`Sandboxie/core/svc/PipeServer.cpp`.

The relevant data nodes are:

```text
SbieSvc LPC port name
PipeServer port security descriptor
client AppContainer token package/capability SID half
regular user/group SID half
NtConnectPort result
SbieDll_CallServer logging and reply path
```

## Official Shape

Microsoft documents AppContainer access as a dual-principal model: access to a
protected resource depends on both the normal user/group side and the
AppContainer package/capability side. Microsoft also documents that named
objects in user/global sessions are not accessible to Windows Store apps by
default, and shows the stable interoperability shape: create a security
descriptor that grants the logon side plus the All AppContainers SID.

Microsoft documents the SDDL `AC` SID alias as All App Packages / all
applications running in an app package context. Microsoft security guidance
also says a NULL DACL grants all access and should not be used as a normal DACL
construction strategy.

```text
https://learn.microsoft.com/en-us/windows/win32/secauthz/implementing-an-appcontainer
https://learn.microsoft.com/en-us/windows/win32/api/securityappcontainer/nf-securityappcontainer-getappcontainernamedobjectpath
https://learn.microsoft.com/en-us/windows/win32/secauthz/sid-strings
https://learn.microsoft.com/en-us/windows/win32/secauthz/null-dacls-and-empty-dacls
https://learn.microsoft.com/en-us/windows/win32/secbp/creating-a-dacl
```

## Schema

Local schema:

```text
docs/plan/srev-081-pipeserver-appcontainer-port-dacl.schema.json
```

The service-port access contract is:

```text
the service side owns the named port security descriptor
the client side must not bypass AppContainer token semantics to connect
normal clients keep the legacy any-process connect shape through WD
AppContainer clients need an explicit AC ACE on systems that understand AC
older systems that do not know AC fall back to an explicit WD DACL
the port must not be published with a NULL DACL
```

## Topology

```text
PipeServer::Start
  -> explicit SDDL DACL
  -> NtCreatePort("\\RPC Control\\SbieSvcPort")
  -> SbieDll_ConnectPort / NtConnectPort
  -> SbieDll_CallServer request/reply protocol
```

The access decision belongs at the service port owner, not in `callsvc.c` by
temporarily changing or bypassing the caller token.

## Logic Risk

Before the SREV-081 patch, `PipeServer::Start` created the public service port with a
NULL DACL because the local comment wanted any process to connect. That relies
on an implicit "no access control" shape while `callsvc.c` admitted
AppContainer service availability was not solved. For AppContainer clients, the official
shape requires an AppContainer package/capability SID grant, not just ordinary
user/group access.

## Fix

`PipeServer::Start` now creates the server port with an explicit SDDL DACL:

```text
O:SYG:SYD:(A;;GA;;;WD)(A;;GA;;;AC)
```

`WD` preserves the legacy any-process connect intent for ordinary clients, and
`AC` grants the AppContainer half of the dual-principal access check. If the OS
does not recognize the `AC` SDDL alias, the service falls back to an explicit
legacy `WD` DACL rather than publishing a NULL DACL.

## Acceptance Gate

`docs/plan/check-srev-081.py` validates the draft-07 schema, official
references, `PipeServer.cpp` SDDL include, explicit `WD` plus `AC` DACL,
legacy fallback DACL, `LocalFree` ownership, NULL-DACL removal, client-side
comment routing to the service-owned DACL boundary, and ledger entry.

Windows gate: normal sandbox clients still connect to the SbieSvc port;
AppContainer sandbox clients can connect when the OS supports the All
AppContainers SID; older OS builds that do not recognize `AC` still start the
service with the legacy explicit `WD` DACL.
