# SREV-187: SCM Event Log Fake Handle Contract

## Data

Owner files:

```text
Sandboxie/core/dll/scm_event.c
Sandboxie/core/dll/scm.c
```

Reviewed nodes:

```text
HANDLE_EVENT_LOG
Scm_RegisterEventSourceW
Scm_RegisterEventSourceA
Scm_DeregisterEventSource
Scm_ReportEventW
Scm_ReportEventA
Scm_CloseEventLog
P_RegisterEventSource
P_DeregisterEventSource
P_ReportEvent
P_CloseEventLog
```

## Schema

`SCM_EVENT_LOG_FAKE_HANDLE_CONTRACT` defines these local contracts:

- `scm_event.c` owns the DLL-side event-log write suppression policy for sandboxed processes.
- `RegisterEventSourceW` returns only the Sandboxie fake event-log handle and does not open a host event-log writer.
- `RegisterEventSourceA` must check `RtlAnsiStringToUnicodeString` before passing the converted source name to the W path.
- `ReportEventA/W` consume a handle returned by `RegisterEventSource`; only `HANDLE_EVENT_LOG` is a valid local write-suppression handle.
- `DeregisterEventSource` consumes a handle returned by `RegisterEventSource`; only `HANDLE_EVENT_LOG` is a valid local handle to close.
- Invalid or non-local event-source handles fail with `ERROR_INVALID_HANDLE`; they are not reported as successful host writes.
- `CloseEventLog` remains separate and passes non-local event-log handles to the native `CloseEventLog` owner.
- The `ReportEventA/W` local prototypes keep the official pointer-to-string-array shape even though the local policy suppresses the write.
- This SREV does not add host event-log brokering, does not change service-control APIs, and does not change read-side event-log handles.
- Windows build/runtime proof is required.

## Topology

The legal local event-log write route is:

```text
RegisterEventSourceA/W
  -> local fake HANDLE_EVENT_LOG
  -> ReportEventA/W suppresses host write only for HANDLE_EVENT_LOG
  -> DeregisterEventSource closes only HANDLE_EVENT_LOG
```

The separate read/close route is:

```text
OpenEventLog or other native event-log handle
  -> CloseEventLog
  -> native __sys_CloseEventLog
```

`ReportEvent` and `DeregisterEventSource` do not use that read/close route.

## Logic Risk

Before this SREV, `Scm_RegisterEventSourceA` ignored the `NTSTATUS` from
`RtlAnsiStringToUnicodeString` and always passed `uni.Buffer` to the W path. On
conversion or allocation failure, the local hook could use an unproven output
buffer and still report success.

`Scm_DeregisterEventSource`, `Scm_ReportEventW`, and `Scm_ReportEventA` also
returned success for every handle value. That made the fake event-log write
policy broader than its local handle owner: callers could pass an invalid or
non-local event-source handle and still receive a success result.

## Official Shape

Microsoft documents `RegisterEventSourceA` as returning a handle to the event
log on success, `NULL` on failure, and says `DeregisterEventSource` closes that
handle. Microsoft documents `ReportEventA` as receiving the event-log handle
returned by `RegisterEventSource` and as taking an array of string pointers.
Microsoft documents `RtlAnsiStringToUnicodeString` as returning `NTSTATUS`; when
allocation is requested, a successful conversion owns a buffer that must be
freed with `RtlFreeUnicodeString`.

Sources:

- https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-registereventsourcea
- https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-reporteventa
- https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-deregistereventsource
- https://learn.microsoft.com/en-us/windows/win32/api/winternl/nf-winternl-rtlansistringtounicodestring

## Fix

`Scm_RegisterEventSourceA` now initializes `uni.Buffer`, checks
`RtlAnsiStringToUnicodeString`, maps conversion failure to a Win32 last-error,
and frees only a proven allocated buffer.

`Scm_DeregisterEventSource`, `Scm_ReportEventW`, and `Scm_ReportEventA` now
return success only for `HANDLE_EVENT_LOG`. Other handles fail with
`ERROR_INVALID_HANDLE`, preserving the no-host-write policy without reporting a
false successful write.

The `ReportEventA/W` prototypes now use pointer-to-string-array parameters.

## Acceptance Gate

Source gate:

```bash
python3 docs/plan/check-srev-187.py
bash docs/plan/check-srev-187.sh
```

Runtime gate still required:

- Windows DLL build for `advapi32.dll` event-log hooks.
- Sandboxed `RegisterEventSourceA/W` + `ReportEventA/W` + `DeregisterEventSource`
  smoke proving fake-handle success and no host event-log write.
- Invalid/non-local event-source handle smoke proving `ERROR_INVALID_HANDLE`.
- `CloseEventLog` smoke proving non-local close still routes to native close.
