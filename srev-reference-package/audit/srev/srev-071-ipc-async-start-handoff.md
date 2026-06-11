# SREV-071: IPC Async Start Handoff

## Data

`Sandboxie/core/dll/ipc_start.c` starts `SandboxieRpcSs` or
`SandboxieDcomLaunch` and waits for the service init event. In async mode, the
function packages `TruePath`, `service`, `hServerEvent`, and `hServerProcess`
into a four-slot payload and transfers that payload plus both wait handles to
`Ipc_StartServer_Thread`.

The relevant data nodes are:

```text
async handoff payload
hServerEvent wait/cleanup handle
hServerProcess wait/cleanup handle
CreateThread return handle
sync wait fallback
```

## Official Shape

Microsoft documents `CreateThread` as returning a thread handle on success and
`NULL` on failure. Its `lpParameter` is the pointer passed to the thread
function:

```text
https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-createthread
```

Microsoft documents `PROCESS_INFORMATION` as containing the created process and
thread handles, and says successful process creation requires closing `hProcess`
and `hThread` when finished:

```text
https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/ns-processthreadsapi-process_information
```

Microsoft documents `WaitForMultipleObjects` as waiting on an array of object
handles, including event and process handles:

```text
https://learn.microsoft.com/en-us/windows/win32/api/synchapi/nf-synchapi-waitformultipleobjects
```

## Schema

Local schema:

```text
docs/plan/srev-071-ipc-async-start-handoff.schema.json
```

The async handoff is legal only when:

```text
payload allocation succeeds
CreateThread returns a non-null thread handle
```

If either gate fails, ownership of `hServerEvent` and `hServerProcess` remains
in the current call and the function must fall back to the synchronous wait and
cleanup path.

## Topology

```text
server process start -> event/process handles -> async payload -> worker thread
                                             \-> sync wait fallback
```

The async worker owns the payload and wait handles only after `CreateThread`
succeeds. Before that point, the current call still owns cleanup.

## Logic Risk

Before this patch, async mode wrote into the payload immediately after
`Dll_AllocTemp` without checking allocation success. If `CreateThread` failed,
the payload was not freed, and `hServerEvent` / `hServerProcess` were not closed
or waited on by the synchronous path. That converts an async optimization into a
handle leak and a lost service-start observation.

## Fix

The async branch now checks the payload allocation before writing the four
handoff slots. If allocation fails, or if `CreateThread` returns `NULL`, it sets
`Async = FALSE`; the existing synchronous wait block then waits on the service
event/process and closes the owned handles. If `CreateThread` fails after the
payload was allocated, the payload is freed before falling back.

## Acceptance Gate

`docs/plan/check-srev-071.py` validates the draft-07 schema, official Microsoft
references, payload allocation gate before slot writes, CreateThread failure
fallback, payload cleanup, `if (! Async)` synchronous fallback shape, and ledger
entry.

Windows gate: normal async service-start handoff still runs on a worker thread;
payload allocation failure and `CreateThread` failure wait synchronously and
close `hServerEvent` / `hServerProcess`; server process early-exit detection
still logs the existing service-start failures.
