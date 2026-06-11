# SREV-113 Service Entry Resource Lifetime

## Data

Owner file:

```text
Sandboxie/core/svc/main.cpp
```

Reviewed nodes:

```text
WinMain
DriverAssist::InitializeSidCache
DriverAssist::DestroySidCache
GetCommandLine
ComServer::RunSlave
ServiceServer::RunUacSlave
NetApiServer::RunSlave
GuiServer::RunSlave
UserServer::RunWorker
StartServiceCtrlDispatcher
ServiceMain
InitializeEventLog
OpenEventLog
CloseEventLog
ServiceHandlerEx
SetServiceStatus
```

## Schema

`SERVICE_ENTRY_RESOURCE_LIFETIME` defines these local contracts:

- `WinMain` owns process-wide initialization before the service dispatcher or
  proxy worker path.
- `DriverAssist::InitializeSidCache` initializes a process-local critical
  section before any service/proxy path can use SID cache lookup.
- Every local return path from `WinMain` after SID cache initialization must
  call `DriverAssist::DestroySidCache`.
- Proxy command-line detection order and proxy worker dispatch targets are
  unchanged.
- `StartServiceCtrlDispatcher` remains the SCM boundary for the normal service
  path.
- A failed `StartServiceCtrlDispatcher` preserves its `GetLastError` return
  code after SID cache cleanup.
- `InitializeEventLog` owns the event-log handle opened by `OpenEventLog`.
- Any opened event-log handle is closed with `CloseEventLog` when service
  initialization fails after event-log open or when STOP/SHUTDOWN cleanup runs.
- SCM status transitions and accepted controls are unchanged.

## Topology

Process entry path:

```text
WinMain
  -> cache module handles and system info
  -> DriverAssist::InitializeSidCache
  -> optional proxy route from GetCommandLine
      -> RunSlave / RunWorker
      -> DriverAssist::DestroySidCache
      -> return NO_ERROR
  -> StartServiceCtrlDispatcher
      -> ServiceMain
      -> ServiceHandlerEx on STOP/SHUTDOWN
  -> DriverAssist::DestroySidCache
  -> return dispatcher result
```

Service event-log path:

```text
ServiceMain
  -> InitializeEventLog
      -> OpenEventLog(NULL, ServiceName)
  -> later initialization
      -> failure: CloseEventLog(EventLog), EventLog = NULL, report STOPPED
      -> success: keep EventLog for LogEvent
  -> ServiceHandlerEx(STOP/SHUTDOWN)
      -> shutdown servers/driver/mount manager
      -> CloseEventLog(EventLog), EventLog = NULL
      -> SetServiceStatus(STOPPED)
```

## Logic Risk

The old entry path initialized the SID cache critical section before checking
for proxy worker modes. Each proxy branch returned directly after the worker
returned, so the matching `DeleteCriticalSection` edge was skipped. A failed
`StartServiceCtrlDispatcher` also returned before SID cache cleanup.

The event-log handle had the opposite shape: `InitializeEventLog` opened a
handle and stored it globally for `LogEvent`, but neither STOP/SHUTDOWN cleanup
nor service-initialization failure closed it.

These are local lifetime issues. They do not require changing command-line
markers, proxy routing, SCM service registration, status values, accepted
controls, or log message formatting.

## Official Shape

- https://learn.microsoft.com/en-us/windows/win32/api/processenv/nf-processenv-getcommandlinew
- https://learn.microsoft.com/en-us/windows/win32/api/winsvc/nf-winsvc-startservicectrldispatcherw
- https://learn.microsoft.com/en-us/windows/win32/services/service-servicemain-function
- https://learn.microsoft.com/en-us/windows/win32/api/winsvc/nf-winsvc-registerservicectrlhandlerexw
- https://learn.microsoft.com/en-us/windows/win32/api/winsvc/nf-winsvc-setservicestatus
- https://learn.microsoft.com/en-us/windows/win32/sync/critical-section-objects
- https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-openeventlogw
- https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-closeeventlog

## Fix

`WinMain` now routes proxy returns and dispatcher failure through one local
cleanup label after `DriverAssist::InitializeSidCache`. The normal proxy return
value remains `NO_ERROR`; dispatcher failure still returns `GetLastError`;
successful dispatcher completion still returns `NO_ERROR`.

`ServiceMain` now closes `EventLog` if initialization fails after opening the
handle. `ServiceHandlerEx` now closes `EventLog` during STOP/SHUTDOWN cleanup.
Both paths clear the global handle after closing.

Proxy marker matching, proxy dispatch targets, service table entries,
`RegisterServiceCtrlHandlerEx`, `SetServiceStatus` state values, server startup,
driver shutdown, mount-manager shutdown, and `LogEvent` message formatting are
unchanged.

## Acceptance Gate

Source gate:

```bash
python3 docs/plan/check-srev-113.py
bash docs/plan/check-srev-113.sh
```

Runtime gate still required:

- Windows service start/stop matrix proving normal SCM start reaches RUNNING and
  STOP/SHUTDOWN reaches STOPPED.
- Proxy worker launch matrix for Com/UAC/Net/GUI/User proxy command lines.
- Negative `StartServiceCtrlDispatcher` run as console/debug process proving
  cleanup happens while preserving the returned error code.
- Event-log handle observation during initialization failure after
  `OpenEventLog`.
- Service STOP/SHUTDOWN resource observation proving the event-log handle is
  closed before process exit or service restart.
