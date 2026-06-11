# SREV-130: DriverAssist InjectLow Process Handle State

## Stage Gate

| Field | Value |
|---|---|
| Stage | action |
| Input artifact | `Sandboxie/core/svc/DriverAssistInject.cpp`, Microsoft OpenProcess / CloseHandle / GetProcessTimes references |
| Output artifact | `docs/plan/srev-130-driverassist-inject-process-handle-state.schema.json`, `docs/plan/check-srev-130.py`, `docs/plan/check-srev-130.sh`, ledger row |
| Owner | `DriverAssist::InjectLow` and `DriverAssist::InjectLow_OpenProcess` |
| Acceptance gate | source checker plus full SREV/KPATH/core coverage matrix; Windows injection runtime remains required |

## Evidence

`Sandboxie/core/svc/DriverAssistInject.cpp` was the highest-ranked unnamed reviewable core file after SREV-129. `DriverAssist::InjectLow` can leave before opening the target process when `m_DriverReady` is false. The shared `finish` block later checks `if (hProcess)` before reporting an injection failure to the driver and closing the process handle.

The old code declared `HANDLE hProcess = InjectLow_OpenProcess(_msg);` after the first early exit. That made the cleanup state depend on a handle variable that did not have an initialized owner state on every path into `finish`.

Microsoft documents `OpenProcess` as returning an open process handle on success and `NULL` on failure, and says the returned handle should be closed with `CloseHandle` when finished. Microsoft documents `CloseHandle` as taking a valid handle to an open object and invalidating the object handle. Microsoft documents `GetProcessTimes` as requiring a process handle with query rights and returning process creation time data only on success. `InjectLow_OpenProcess` uses exactly this shape: open a process, verify creation time with `GetProcessTimes`, return the handle only on match, otherwise close local handle and return `NULL`.

Official references:

- https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-openprocess
- https://learn.microsoft.com/en-us/windows/win32/api/handleapi/nf-handleapi-closehandle
- https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-getprocesstimes

## Data

`DriverAssist::InjectLow`, `DriverAssist::InjectLow_OpenProcess`, `hProcess`, `m_DriverReady`, `errlvl`, `SVC_PROCESS_MSG::process_id`, `SVC_PROCESS_MSG::create_time`, `OpenProcess`, `GetProcessTimes`, `CloseHandle`, `SbieDll_InjectLow`, `GuiServer::InitProcess`, `MountManager::AcquireBoxRoot`, `SbieApi_Call(API_INJECT_COMPLETE, ...)`, `file_root_path`, and `reg_root_path`.

## Schema

`DRIVERASSIST_INJECT_PROCESS_HANDLE_STATE` says:

- `InjectLow` owns a process handle state variable initialized to `NULL` before any `finish` edge.
- `InjectLow_OpenProcess` returns a real process handle only after `OpenProcess` succeeds and creation time matches.
- `OpenProcess` failure and creation-time mismatch leave `InjectLow` `hProcess` as `NULL`.
- `finish` cleanup tests only the initialized `hProcess` state before `API_INJECT_COMPLETE` failure notification and `CloseHandle`.
- `CloseHandle` is called only for a non-null process handle produced by `InjectLow_OpenProcess`.
- Driver-not-ready early exit does not read an uninitialized process handle.
- Path allocation cleanup remains independent from process handle cleanup.
- Successful injection, `GuiServer`, `MountManager`, and `API_INJECT_COMPLETE` topology are unchanged.
- Failed injection still reports `API_INJECT_COMPLETE` error only when a target process handle was legally opened.

## Topology

The legal handle topology is:

```text
hProcess = NULL
  -> optional InjectLow_OpenProcess
  -> OpenProcess success and GetProcessTimes creation-time match
  -> hProcess owns open target-process handle
  -> injection / GUI / mount / driver-complete path
  -> finish
  -> if hProcess then optional failure notification and CloseHandle
```

The corrected early-exit topology is:

```text
driver not ready
  -> errlvl = 0xFF
  -> finish
  -> hProcess == NULL
  -> no process-handle notification
  -> no CloseHandle
```

## Logic Risk

The cleanup block is a join point for paths before and after process-handle acquisition. A join point needs a legal state value for every resource it tests. The previous source declared `hProcess` only on the acquisition path, but `finish` also runs from paths before acquisition. In a process-injection broker, reading an uninitialized handle value can turn an early failure into a false `API_INJECT_COMPLETE` failure notification or an invalid `CloseHandle`.

The correct local repair is to make process-handle ownership explicit from the top of the function with a `NULL` sentinel. No injection policy, process access mask, creation-time verification, path cleanup, GUI job assignment, mount, or driver notification success path changes.

## Fix

`DriverAssist::InjectLow` now declares `HANDLE hProcess = NULL;` with the other resource state variables before the first `goto finish`. The later open step assigns `hProcess = InjectLow_OpenProcess(_msg);`. All cleanup paths now test an initialized handle state.

## Acceptance Gate

`docs/plan/check-srev-130.py` validates the draft-07 schema, official references, handle owner initialization before the first finish edge, assignment from `InjectLow_OpenProcess`, absence of the stale declaration-at-open pattern, `InjectLow_OpenProcess` open/time-match/close topology, successful injection topology preservation, failure cleanup preservation, and ledger entry. `docs/plan/check-srev-130.sh` is the matrix wrapper.

Runtime/build gate: Windows service build for `DriverAssistInject.cpp`, driver-not-ready injection request proving no invalid handle read, `OpenProcess` failure injection proving cleanup skips process-handle actions, creation-time mismatch proving the temporary handle closes inside `InjectLow_OpenProcess`, and later failure after successful open proving exactly one failure notification and one close.
