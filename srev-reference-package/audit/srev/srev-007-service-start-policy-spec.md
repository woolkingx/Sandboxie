# SREV-007 Service Start Broker Policy Posture

Status: comment/policy classification after official SCM access review; no behavior change.

## Official Shape

`OpenServiceW` opens an existing service by name. Before granting requested
access, Windows checks the calling process access token against the service
object security descriptor.

`StartServiceW` requires the service handle to have `SERVICE_START`. If the
handle lacks that access right, `StartServiceW` fails with
`ERROR_ACCESS_DENIED`.

The SCM itself has a separate security descriptor. `SC_MANAGER_CONNECT` is the
right required to connect to the Service Control Manager; `SERVICE_START` is the
service-object right required to start a service.

Sources:

- https://learn.microsoft.com/en-us/windows/win32/api/winsvc/nf-winsvc-openservicew
- https://learn.microsoft.com/en-us/windows/win32/api/winsvc/nf-winsvc-startservicew
- https://learn.microsoft.com/en-us/windows/win32/services/service-security-and-access-rights
- https://learn.microsoft.com/en-us/windows/win32/api/winsvc/nf-winsvc-openscmanagerw

## Local Topology

`ServiceServer::Handler` calls `PipeServer::ImpersonateCaller(&msg)` before
dispatching `MSGID_SERVICE_START`.

Therefore `OpenSCManager`, `OpenService`, and `StartService` run under the
client's impersonated token on the service worker thread. SCM/service DACL checks
are still real authorization gates.

## Local Policy Contract

The old source comment in `StartHandler` said an admin check should be
performed. That is not the current legal owner model. Because the service worker
is impersonating the caller, the host service object's SCM DACL is the current
authorization owner for `SERVICE_START`.

A direct `IsAdmin()` or elevation-style gate would be stricter than Windows
service DACL semantics and could break services that intentionally grant
`SERVICE_START` to a non-admin identity. If Sandboxie wants a stricter policy,
the owner must be explicit:

```text
admin-only
explicit StartService allowlist
configurable sandbox rule
```

## Decision Boundary

The existing source-level SREV-006B gate already ensures malformed service names
do not reach SCM. SREV-007 is now a source comment and policy-classification
patch: the current behavior remains SCM DACL delegation under caller
impersonation. A future stricter Sandboxie policy must be a named policy change,
not a silent replacement of SCM DACL semantics.

## Acceptance Gate

- Source gate proves `ServiceServer::Handler` impersonates the caller before
  dispatch, `StartHandler` validates the service name before SCM, and the source
  comment rejects blind admin-only/elevation gates.
- Runtime smoke proves a sandboxed non-admin caller without `SERVICE_START` on
  the target host service receives `ERROR_ACCESS_DENIED`.
- Runtime smoke identifies whether any supported non-admin service-start flow
  relies on a deliberate service DACL grant.
- If Sandboxie chooses a stricter policy, the patch must name the new owner:
  admin-only, explicit `StartService` allowlist, or another setting. It must not
  silently replace SCM DACL semantics without compatibility evidence.
