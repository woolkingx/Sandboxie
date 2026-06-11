# SREV-065: SCM Sppsvc Handle Lifetime

## Data

`Sandboxie/core/dll/scm_misc.c` starts the host `sppsvc` service for a specific
RPC binding workaround. The helper opens the service control manager, opens the
service, starts it, polls service state, and then closes opened handles.

The relevant data nodes are:

```text
SCM handle from Scm_OpenSCManagerW
sppsvc service handle from Scm_OpenServiceWImpl
StartService result path
QueryServiceStatus polling path
CloseServiceHandle ownership edge
```

## Official Shape

Microsoft documents `OpenSCManagerW` as returning an SCM database handle that
can be closed by `CloseServiceHandle`:

```text
https://learn.microsoft.com/en-us/windows/win32/api/winsvc/nf-winsvc-openscmanagerw
```

Microsoft documents `OpenServiceW` as returning a service handle:

```text
https://learn.microsoft.com/en-us/windows/win32/api/winsvc/nf-winsvc-openservicew
```

Microsoft documents `CloseServiceHandle` as closing handles to service control
manager objects and service objects:

```text
https://learn.microsoft.com/en-us/windows/win32/api/winsvc/nf-winsvc-closeservicehandle
```

## Schema

Local schema:

```text
docs/plan/srev-065-scm-sppsvc-handle-lifetime.schema.json
```

Ownership:

```text
Scm_OpenSCManagerW -> handle1 -> Scm_CloseServiceHandleImpl(handle1)
Scm_OpenServiceWImpl -> handle2 -> Scm_CloseServiceHandleImpl(handle2)
```

The service handle must remain in the outer lifetime slot so the function's
single cleanup section can close it.

## Topology

```text
SCM open -> service open -> start/poll service -> close service handle -> close SCM handle
```

`Scm_Start_Sppsvc` owns the local lifetime of both handles. Neither handle is
transferred to another owner.

## Logic Risk

Before this patch, `Scm_Start_Sppsvc` declared an outer `handle2 = NULL`, then
declared another inner `SC_HANDLE handle2` inside the `if (handle1)` block. The
inner handle was used for `StartService` and `QueryServiceStatus`, but the outer
handle stayed `NULL`. The final cleanup block therefore closed only `handle1`
and skipped the opened service handle.

## Fix

The service-open result is now assigned to the outer `handle2` lifetime slot.
The existing cleanup block closes both `handle1` and `handle2` when present.

## Acceptance Gate

`docs/plan/check-srev-065.py` validates the draft-07 schema, official reference
links, absence of the inner `SC_HANDLE handle2` shadow, assignment into the
outer lifetime slot, and both handle cleanup calls.

Windows gate: `Scm_Start_Sppsvc` should still start/poll `sppsvc` when allowed,
close both SCM and service handles on success, and close already-opened handles
on service open/start/query failure paths.
