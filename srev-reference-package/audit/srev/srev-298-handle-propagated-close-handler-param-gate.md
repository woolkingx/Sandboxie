# SREV-298: Handle Propagated Close Handler Param Gate

## Stage Gate

| Field | Value |
|---|---|
| Stage | schema -> boundary -> topology -> logic -> verify |
| Input artifact | `Sandboxie/core/dll/handle.c`, `Sandboxie/core/dll/handle.h`, SREV-070, Microsoft `DuplicateHandle` / `ZwDuplicateObject` references |
| Output artifact | Local propagation contract, draft-07 schema, targeted checker, ledger fragment |
| Owner | `Handle_RegisterHandler` and `Handle_SetupDuplicate` close-handler metadata propagation |
| Acceptance gate | Targeted checker validates the bPropagate/Param gate, duplicate setup propagation shape, current caller shape, stale todo removal, SREV-070 adjacency, official references, and ledger fragment |

## Data

`handle.c` owns per-handle metadata that Windows does not own:

```text
HANDLE_STATE.CloseHandlers
HANDLE_HANDLER.Close callback
HANDLE_HANDLER.Param
HANDLE_HANDLER.bPropagate
Handle_SetupDuplicate(old_handle, new_handle)
```

`Handle_SetupDuplicate` is called after a same-process duplicate succeeds in
`secure.c`. It copies `RelocationPath`, `KeyWow64Flags`, and the first
propagated close handler to the new handle. Before this SREV, the source
comment already admitted that `bPropagate` was incompatible with `Param`, and
`Handle_SetupDuplicate` registered the propagated handler on the new handle
with `NULL` param.

Current source users register a propagated close handler only for file recovery:

```text
Handle_RegisterHandler(FileHandle, File_NotifyRecover, NULL, TRUE)
```

## Official Shape

Microsoft documents `DuplicateHandle` as duplicating an object handle from a
source process handle table into a target process handle table. Microsoft
documents options such as `DUPLICATE_CLOSE_SOURCE` and
`DUPLICATE_SAME_ACCESS`.

Microsoft documents `ZwDuplicateObject` as the native duplicate-object
operation with similar source process, source handle, target process, target
handle, access, attributes, and options fields.

Those APIs duplicate OS handle table entries. They do not duplicate Sandboxie
private metadata stored in `HANDLE_STATE.CloseHandlers`; that metadata is a
local `handle.c` owner contract.

Official references:

- `https://learn.microsoft.com/en-us/windows/win32/api/handleapi/nf-handleapi-duplicatehandle`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/nf-ntifs-zwduplicateobject`

## Schema

Local schema:

```text
docs/plan/srev-298-handle-propagated-close-handler-param-gate.schema.json
```

Contract id:

```text
HANDLE_PROPAGATED_CLOSE_HANDLER_PARAM_GATE
```

## Boundary

```text
Handle_RegisterHandler
  -> owns admission of HANDLE_HANDLER.Close / Param / bPropagate

Handle_SetupDuplicate
  -> after OS duplicate succeeds
  -> copies only local metadata with legal duplicate shape
```

Since no duplicate-param owner exists today, propagated close handlers are legal
only when `Param == NULL`.

Contract summary:

```text
propagated close handlers are legal only when `Param == NULL`
```

## Topology

```text
DuplicateHandle / NtDuplicateObject
  -> OS handle table entry duplicate
  -> secure.c calls Handle_SetupDuplicate for same-process target
  -> handle.c propagates only metadata with local duplicate contract
```

SREV-070 owns close-handler node lifetime. SREV-298 owns the propagated
handler's parameter legality across duplicated handles.

## Logic Risk

The previous code silently converted any propagated handler's `Param` to
`NULL` during duplicate setup. That is safe for the current `File_NotifyRecover`
caller, but it would silently corrupt a future propagated handler that expects a
non-null parameter. The correct local contract is fail-closed admission until a
real duplicate-param owner exists.

The stale commented-out log line also made duplicate registration look like an
unfinished runtime behavior. The actual behavior is clear: duplicate
registration returns `FALSE` and keeps the existing handler.

## Fix

`Handle_RegisterHandler` now rejects `bPropagate && Params` before inserting a
handler node. The `HANDLE_HANDLER.bPropagate` source comment now records the
SREV-298 contract. The stale duplicate-registration todo comment was replaced
with a behavior comment.

No existing propagated caller changes behavior because current propagated
registration uses `Param == NULL`. No `Handle_SetupDuplicate` copy of
`RelocationPath`, `KeyWow64Flags`, or close-handler callback identity changed.

## Acceptance Gate

`docs/plan/check-srev-298.py` validates the draft-07 schema, official
references, source admission gate, duplicate setup's continued `NULL` param
propagation, current propagated caller shape, stale todo removal, SREV-070
adjacency, combined ledger entry, and split ledger fragment.

Runtime gate: Windows duplicate-handle smoke proving file recovery metadata
still propagates for `File_NotifyRecover` and a negative unit/runtime probe
proving `bPropagate && Params` fails registration.
