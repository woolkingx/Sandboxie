# SREV-299: IPC CreateObjects Bootstrap Allocation Gate

## Stage Gate

| Field | Value |
|---|---|
| Stage | schema -> boundary -> topology -> logic -> verify |
| Input artifact | `Sandboxie/core/dll/ipc.c`, SREV-037, Microsoft object-directory, event-object, object-query, and symbolic-link references |
| Output artifact | Bootstrap allocation/handle cleanup contract, draft-07 schema, targeted checker, ledger fragment |
| Owner | `Ipc_CreateObjects` BaseNamedObjects bootstrap path discovery and object-link creation |
| Acceptance gate | Targeted checker validates dummy-event cleanup, path-buffer allocation gates, SREV-037 adjacency, source comment replacement, official references, and ledger fragment |

## Data

`Ipc_CreateObjects` runs in the first process in a box when alternate IPC naming
is disabled. It creates a named dummy event under the sandboxed
`BaseNamedObjects` namespace, queries that object's name through `Ipc_GetName`,
trims the dummy event leaf from `CopyPath`, and then creates the sandboxed
object-manager topology:

```text
CopyPath
  -> main BaseNamedObjects directory
  -> BNOLINKS directory
  -> Global / Local / Session symbolic links
```

The old source comment admitted that the path discovery still uses a dummy
object rather than a full symbolic-link reparse design. Around that comment,
the function allocated `buffer`, `BNOLINKS`, `buffer2`, and `GLOBAL`, then
immediately wrote through those pointers. If `Ipc_GetName` failed after
`CreateEvent` succeeded, the dummy event handle also skipped the existing
`NtClose(handle)` path.

## Official Shape

Microsoft documents object directories as object-manager containers for named
kernel objects; they do not correspond to file-system directories.

Microsoft documents `CreateEventW` as creating or opening a named event object
and returning an object handle.

Microsoft documents kernel objects as handle-owned objects; event handles
returned by `CreateEvent` are closed through `CloseHandle` in Win32. This code
uses the native `NtClose` owner for the same handle.

Microsoft documents `NtQueryObject` as retrieving object information from a
handle and reporting required buffer length when the output buffer is too small.
`Ipc_GetName` is the local wrapper that maps a handle/object name into
`TruePath` and `CopyPath`.

Microsoft documents symbolic-link creation as a boundary between a symbolic
link name and target name. SREV-037 owns the driver-side counted-string and
boxed-path gate for `SbieApi_CreateDirOrLink`.

Official references:

- `https://learn.microsoft.com/en-us/windows-hardware/drivers/kernel/object-directories`
- `https://learn.microsoft.com/en-us/windows/win32/api/synchapi/nf-synchapi-createeventw`
- `https://learn.microsoft.com/en-us/windows/win32/sysinfo/kernel-objects`
- `https://learn.microsoft.com/en-us/windows/win32/api/winternl/nf-winternl-ntqueryobject`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-iocreatesymboliclink`

## Schema

Local schema:

```text
docs/plan/srev-299-ipc-createobjects-bootstrap-allocation-gate.schema.json
```

Contract id:

```text
IPC_CREATEOBJECTS_BOOTSTRAP_ALLOCATION_GATE
```

## Boundary

```text
CreateEvent dummy object handle
  -> Ipc_GetName
  -> CopyPath base directory
  -> SbieApi_CreateDirOrLink object-directory / symbolic-link creation
```

`Ipc_CreateObjects` owns only local bootstrap storage and dummy-handle cleanup.
SREV-037 owns the driver API boundary that creates directories and symbolic
links from counted strings. A future full symbolic-link reparse design remains
separate from this allocation/cleanup owner.

Contract summary:

```text
SREV-037 owns the driver-side counted-string and boxed-path gate
SREV-037 must accept the box-level BNOLINKS bootstrap auxiliary path without
broadening normal IPC path creation
```

## Topology

```text
Win32 named event -> object-manager name query -> sandbox CopyPath
  -> box-level BNOLINKS bootstrap auxiliary directory
  -> BNOLINKS / BaseNamedObjects / Global / Local / Session topology
```

Runtime capture on Windows proved that building `BNOLINKS` as a sibling of the
session IPC root (`\Sandbox\%USER%\%SANDBOX%\BNOLINKS`) conflicts with the
initial SREV-037 driver gate. A follow-up runtime test proved that moving
`BNOLINKS` under `Dll_BoxIpcPath` removes `SBIE2308` but can make `Start.exe`
hit the name-buffer depth guard before launching targets. The legal topology
therefore keeps the original box-level `BNOLINKS` auxiliary directory and
requires SREV-037 to accept only that same-box bootstrap subtree.

The legal local transition is:

```text
buffer allocation proved
  -> string copy/concat
  -> SbieApi_CreateDirOrLink
```

If a bootstrap allocation fails, the function must log the local error level,
close any still-owned dummy event handle, free previously allocated buffers, and
stop before writing through missing storage.

## Logic Risk

The earlier code wrote through `buffer`, `BNOLINKS`, `buffer2`, and `GLOBAL`
without proving allocation success. Low-memory failure could therefore turn IPC
namespace bootstrap into a null write before the driver-side boxed-path gate is
even reached. The dummy event handle was also not closed on the `Ipc_GetName`
failure path.

The old comment also mixed two different concerns: the broader symbolic-link
reparse design and the local bootstrap implementation. This SREV does not
claim the reparse design is solved; it records that as a separate gate while
closing the local allocation/handle owner.

## Fix

`Ipc_CreateObjects` now initializes the dummy event handle to `NULL`, clears it
after the normal `NtClose`, and closes it in `finish` if an earlier path still
owns it. The function now gates `buffer`, `BNOLINKS`, `buffer2`, and `GLOBAL`
allocations with `STATUS_INSUFFICIENT_RESOURCES` before any string write.
`BNOLINKS` remains a box-level bootstrap auxiliary directory; SREV-037 owns the
narrow driver-side exception that permits only this same-box auxiliary subtree
in addition to the configured IPC root.

The stale `todo/fix-me` source comment was replaced with an SREV-299 topology
comment that separates the current dummy-event path discovery from the future
symbolic-link reparse design gate.

## Acceptance Gate

`docs/plan/check-srev-299.py` validates the draft-07 schema, official
references, source allocation gates before first writes, dummy event handle
cleanup, SREV-037 adjacency, stale comment removal, combined ledger entry, and
split ledger fragment.

Runtime gate: Windows IPC namespace bootstrap under normal startup, forced
`Ipc_GetName` failure, and allocation-failure injection for each bootstrap
buffer. The broader symbolic-link reparse design remains open.
