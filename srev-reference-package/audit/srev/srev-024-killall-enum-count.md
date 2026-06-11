# SREV-024: KillAll Process Enumeration Count

## Stage Gate

| Field | Content |
|---|---|
| Stage | schema -> topology -> logic -> action |
| Input Artifact | `ProcessServer::KillAll` / `KillAllHelper` process termination path |
| Output Artifact | Source-level deterministic termination-mode and PID-count fix |
| Owner | `ProcessServer` service broker process-kill handler |
| Acceptance Gate | Job termination is only selected by explicit policy, and manual fallback iterates exactly the returned PID count. |

## Official Shape

Microsoft `TerminateJobObject` documentation says the function terminates all
processes associated with the job object:

```text
https://learn.microsoft.com/en-us/windows/win32/api/jobapi2/nf-jobapi2-terminatejobobject
```

Microsoft `TerminateProcess` documentation says the function terminates the
specified process handle:

```text
https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-terminateprocess
```

Those APIs define the executor behavior. They do not define Sandboxie's PID
enumeration contract; that contract is local.

## Local Shape

`SbieApi_EnumProcessEx(..., pids, &count)` passes `count` as the caller capacity
to the driver and receives the number of matching PIDs written back. The driver
side `Process_Enumerate` writes at most `*count` entries and then sets
`*count = num`.

Therefore the valid PID indexes are:

```text
0 <= i < count
```

`count` is not a valid final index.

## Finding

`KillAll` selected the `TerminateJob` mode only in some branches. If the caller
was not boxed and job termination was disabled by `NoAddProcessToJob` or
`NoSecurityIsolation`, `TerminateJob` was left uninitialized before being passed
to `KillAllHelper`.

`KillAllHelper` then manually terminated returned PIDs with:

```text
for (i = 0; i <= count; ++i)
```

That reads one element past the PID array slice returned by the driver.

## Fix

`TerminateJob` now defaults to `FALSE` and is set to `TRUE` only through the
explicit `TerminateJobObject` policy branch.

Manual PID termination now iterates:

```text
for (i = 0; i < count; ++i)
```

## Runtime Gate

Windows runtime proof:

1. `KillAll` with job termination disabled never sends `GUI_KILL_JOB`;
2. manual fallback terminates each returned PID once and never reads a stale
   `pids[count]` value;
3. `TerminateJobObject` enabled boxes still send the GUI job-kill request before
   manual fallback;
4. RPCSS boxed caller still avoids job termination.
