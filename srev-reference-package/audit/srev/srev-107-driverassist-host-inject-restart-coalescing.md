# SREV-107: DriverAssist Host Inject Restart Coalescing

## Data

`Sandboxie/core/svc/DriverAssist.cpp` receives `SVC_CONFIG_UPDATED` datagrams
from the driver. On config reload it refreshes the ini cache, rebuilds syscall
data for low-level injection, and calls `DriverAssist::RestartHostInjectedSvcs`.

That method is a gate in front of the global host-injected service restart job:

```text
SVC_CONFIG_UPDATED
  -> SbieIniServer::NotifyConfigReloaded when another process changed config
  -> SbieDll_InjectLow_InitSyscalls(TRUE)
  -> DriverAssist::RestartHostInjectedSvcs()
  -> ::RestartHostInjectedSvcs() in HostInjectProcessUtil.cpp
```

`HostInjectProcessUtil.cpp` builds the configured `HostInjectProcess` service
set, enumerates active Win32 services through SCM, probes each service process
for `SbieDll.dll`, and stops/starts services that need their host-injection
state changed.

## Official Shape

Microsoft documents `EnumServicesStatusExW` as enumerating services in an SCM
database. The SCM handle must have `SC_MANAGER_ENUMERATE_SERVICE`, and the
buffer must be large enough for an array of `ENUM_SERVICE_STATUS_PROCESS`
records and their strings.

Microsoft documents `OpenSCManagerW` as opening the SCM database after checking
the caller token against the SCM security descriptor. Microsoft documents
`OpenServiceW` as opening a service by service name, not display name, with
requested access checked against the service security descriptor.

Microsoft documents `ControlService` as sending a control code through SCM. SCM
processes service control notifications serially and `ControlService` can block
for 30 seconds if another service is busy handling a control code.

Microsoft documents `StartServiceW` as starting a service through SCM. It can
also block for 30 seconds when another service is busy handling a control code.

Microsoft documents `Sleep` as suspending the current thread for a time interval
based on the system clock and warns that a ready thread is not guaranteed to run
immediately after the interval.

```text
https://learn.microsoft.com/en-us/windows/win32/api/winsvc/nf-winsvc-enumservicesstatusexw
https://learn.microsoft.com/en-us/windows/win32/api/winsvc/nf-winsvc-openscmanagerw
https://learn.microsoft.com/en-us/windows/win32/api/winsvc/nf-winsvc-openservicew
https://learn.microsoft.com/en-us/windows/win32/api/winsvc/nf-winsvc-controlservice
https://learn.microsoft.com/en-us/windows/win32/api/winsvc/nf-winsvc-startservicew
https://learn.microsoft.com/en-us/windows/win32/api/synchapi/nf-synchapi-sleep
```

## Schema

Local schema:

```text
docs/plan/srev-107-driverassist-host-inject-restart-coalescing.schema.json
```

The host-injected service restart coalescing contract is:

```text
each config update increments a generation counter
only one restart worker may be active at a time
the active worker waits for a 250ms quiet window before entering SCM work
the worker must not hold m_critSecHostInjectedSvcs while sleeping
SCM enumeration / stop / start work runs under m_critSecHostInjectedSvcs
if a new generation appears while SCM work is running, a worker must run another quiet-window pass
if another worker claims the new generation, the current worker may exit
the wrapper must not change BuildSvcSet, IsSvcInjected, RestartService, or HostInjectProcess matching policy
```

## Topology

Source topology after this SREV:

```text
RestartGeneration
  <- InterlockedIncrement on every config update request

RestartWorkerActive
  <- InterlockedCompareExchange claims the one active worker

active worker
  -> read RestartGeneration
  -> Sleep(250)
  -> repeat until RestartGeneration is unchanged across the sleep interval
  -> EnterCriticalSection(m_critSecHostInjectedSvcs)
  -> ::RestartHostInjectedSvcs()
  -> LeaveCriticalSection(m_critSecHostInjectedSvcs)
  -> release RestartWorkerActive
  -> exit if no newer generation exists
  -> otherwise reclaim worker role or let another worker handle it
```

The SCM job topology remains in `HostInjectProcessUtil.cpp`:

```text
BuildSvcSet()
  -> OpenSCManagerW(..., SC_MANAGER_ALL_ACCESS)
  -> EnumServicesStatusExW(..., SERVICE_WIN32, SERVICE_ACTIVE, ...)
  -> skip SBIESVC
  -> compare service name to HostInjectProcess set
  -> IsSvcInjected(pid)
  -> RestartService()
       -> OpenService(..., SERVICE_ALL_ACCESS)
       -> ControlService(..., SERVICE_CONTROL_STOP, ...)
       -> StartServiceW(...)
```

## Logic Risk

The old `JobCounter` comment promised that the first caller waited until the
last config-update call before starting the job. The code did not guarantee a
quiet window. Later callers incremented and immediately decremented the counter,
so the first caller usually observed only `1` after its fixed sleep and entered
SCM even if multiple reload requests arrived during the burst.

That mattered because the wrapped operation is SCM stop/start work. Microsoft
documents SCM control notifications as serial and potentially blocking. A noisy
config edit should produce one stable restart pass, not one pass per incidental
reload and not a pass based on a counter that loses recent arrivals.

## Fix

`DriverAssist::RestartHostInjectedSvcs` now uses:

```text
RestartGeneration
RestartWorkerActive
```

Every request increments `RestartGeneration`. Only the thread that successfully
claims `RestartWorkerActive` becomes the worker. The worker waits until
`RestartGeneration` is unchanged across a 250ms sleep interval, then runs
`::RestartHostInjectedSvcs()` under `m_critSecHostInjectedSvcs`. If a newer
generation appears while the SCM job is running, the current worker either
reclaims the worker role for another quiet-window pass or exits because another
thread has already claimed it.

No `HostInjectProcess` config parsing, service matching, module-injection
detection, SCM enumeration, service stop/start access mask, or service restart
policy changed.

## Acceptance Gate

`docs/plan/check-srev-107.py` validates the draft-07 schema, official
references, generation/active-worker source topology, 250ms quiet-window loop,
critical-section placement around SCM work only, stale workaround wording
removal, preservation of `HostInjectProcessUtil.cpp` policy, and ledger entry.
`docs/plan/check-srev-107.sh` is the matrix wrapper.

Runtime gate: Windows service matrix with rapid config reload bursts, reload
during an active SCM restart pass, host-injected service that lacks `SbieDll`,
service that should no longer be injected, `SERVICE_WIN32_SHARE_PROCESS`,
service stop timeout / `ERROR_SERVICE_REQUEST_TIMEOUT`, access-denied service,
and observation that exactly the stable post-burst `HostInjectProcess` policy is
applied.
