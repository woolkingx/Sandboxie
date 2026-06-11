# SREV-315: SCM DLL Service Start Shim

## Stage Gate

| Field | Value |
|---|---|
| Stage | data -> schema -> topology -> logic -> action -> verify |
| Input artifact | `Sandboxie/core/dll/scm_misc.c`, `Sandboxie/core/dll/ldr.c`, Microsoft DirectWrite and service-control documentation |
| Output artifact | DLL-triggered service-start shim contract, draft-07 schema, targeted checker, ledger fragment |
| Owner | `Scm_DllHack`, with `Scm_DWriteDll` and `Scm_OsppcDll` as consumers |
| Acceptance gate | Targeted checker validates official references, local service-start topology, `SERVICE_STOPPED` gate, boxed-service exclusion, `SERVICE_START` access, no claim that `StartServiceW` proves `SERVICE_RUNNING`, source comment boundaries, combined ledger, and ledger fragment |

## Data

`ldr.c` registers `dwrite.dll` with `Scm_DWriteDll`. When DirectWrite loads,
`Scm_DWriteDll` asks `Scm_DllHack` to start `FontCache` if that host service is
currently stopped. The same helper is used by `Scm_OsppcDll` for the Office
`osppsvc` compatibility path.

Before this SREV, the source described these paths as generic hacks. The helper
already had a narrow behavior: skip null modules, skip boxed services, query the
real service state, open the service with `SERVICE_START`, call `StartService`,
sleep briefly only if the call succeeds, and close the service handle.

## Official Shape

Microsoft documents DirectWrite as providing font-system services for font
enumeration, font fallback, and font caching.

Microsoft documents `OpenServiceW` as opening an existing service by service
object name, with access checked against the service object's DACL before the
requested access is granted.

Microsoft documents `StartServiceW` as requiring a service handle with
`SERVICE_START`. For services, it returns after the SCM receives notification
that the service's `ServiceMain` thread was created successfully; callers use
service-status queries to determine whether initialization has finished. It can
also fail if service control handling is busy or times out.

Microsoft documents `QueryServiceStatusEx` as retrieving the most recent status
reported to SCM, using `SC_STATUS_PROCESS_INFO` and
`SERVICE_STATUS_PROCESS`.

Official references:

- `https://learn.microsoft.com/en-us/windows/win32/directwrite/introducing-directwrite`
- `https://learn.microsoft.com/en-us/windows/win32/api/winsvc/nf-winsvc-openservicew`
- `https://learn.microsoft.com/en-us/windows/win32/api/winsvc/nf-winsvc-startservicew`
- `https://learn.microsoft.com/en-us/windows/win32/api/winsvc/nf-winsvc-queryservicestatusex`
- `https://learn.microsoft.com/en-us/windows/win32/services/service-security-and-access-rights`

## Schema

Local schema:

```text
docs/plan/srev-315-scm-dll-service-start-shim.schema.json
```

Contract id:

```text
SCM_DLL_SERVICE_START_SHIM
```

## Topology

```text
dwrite.dll load
  -> Ldr_Dlls entry
  -> Scm_DWriteDll
  -> Scm_DllHack("FontCache")
  -> Scm_QueryServiceByName(..., with_service_status = TRUE)
  -> if state == SERVICE_STOPPED
  -> Scm_OpenServiceWImpl(..., SERVICE_START)
  -> Scm_StartServiceWImpl(...)
  -> optional brief Sleep(500)
  -> Scm_CloseServiceHandleImpl
```

Shared helper boundary:

```text
DLL-load compatibility signal
  -> host service query/start request
  -> SCM owns service state and start authorization
```

Sandboxie owns only the compatibility request. StartServiceW only proves SCM accepted the start request; it does not prove that the host service reached `SERVICE_RUNNING`.

## Logic Risk

Calling this a generic hack hides the important boundary: `StartServiceW` does
not prove the target service is fully running. Treating the helper as a
guaranteed readiness gate would be wrong, especially for services with slow
initialization or control-dispatch delays. Future behavior changes that need
readiness must add a bounded `QueryServiceStatusEx` wait and a Windows runtime
matrix.

## Fix

Source comments now name `Scm_DllHack` as a service-start compatibility shim and
record that `StartServiceW` only proves SCM accepted the start request, not that
the service reached `SERVICE_RUNNING`. The `dwrite.dll` loader entry now names
the DirectWrite FontCache service-start shim, and the Office/FontCache consumer
comments no longer use generic hack wording.

No query, boxed-service skip, open access mask, start call, sleep duration,
handle close, or service name changed.

## Acceptance Gate

`docs/plan/check-srev-315.py` validates the draft-07 schema, official
references, loader table registration, `Scm_DWriteDll -> Scm_DllHack(FontCache)`
topology, shared helper query/start/close behavior, boxed-service skip,
`SERVICE_STOPPED` gate, `SERVICE_START` access, source comments, absence of old
generic hack wording in this owner block, combined ledger entry, and split
ledger fragment.

Runtime gate: Windows DirectWrite/IE 9 FontCache smoke plus Office osppc smoke
proving compatibility is preserved and no caller treats this helper as proof of
full `SERVICE_RUNNING` readiness.
