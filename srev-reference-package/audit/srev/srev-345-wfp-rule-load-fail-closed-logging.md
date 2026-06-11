# SREV-345: WFP Rule Load Fail-Closed Logging Boundary

| Field | Content |
|---|---|
| Stage | schema -> topology -> action -> verify |
| Input artifact | `Sandboxie/core/drv/wfp.c`, SREV-162 driver logging topology, and WFP process refresh source evidence |
| Output artifact | Source comment/topology patch, draft-07 schema, checker, and ledger fragment |
| Owner | `WFP_LoadRules` owns rule-load allocation error logging; `WFP_UpdateProcess` owns per-process fail-closed refresh state and partial-list cleanup |
| Acceptance gate | Targeted checker validates the rule-load failure log owner, no duplicate popup in the refresh path, fail-closed assignment, partial-list cleanup, stale TODO removal, and ledger fragment |

## Data

`WFP_UpdateProcess` refreshes per-process WFP state from the current process and
box settings. When `AllowNetworkAccess` does not already force a full block, it
calls `WFP_LoadRules` to build a fresh `NewNetFwRules` list from matching
`NetworkAccess` settings.

`WFP_LoadRules` initializes the destination list, walks `NetworkAccess` values,
matches each value against the process image, allocates a `NETFW_RULE`, parses
the matched rule, and appends it to the caller-provided list. Its only false
return path today is `NetFw_AllocRule` failure. That path already calls
`Log_Msg_Process(MSG_1201, NULL, NULL, proc->box->session_id, proc->pid)` before
returning `FALSE`.

Before this SREV, `WFP_UpdateProcess` set `BlockInternet = TRUE` on
`WFP_LoadRules` failure and carried a `// todo: log error` comment. That comment
hid the current owner split: the concrete allocation failure is logged by the
rule loader, while the refresh path owns the fail-closed state transition and
cleanup of the partially built rule list.

## Official And Local Shape

No new Windows API edge is introduced by this SREV. The logging sink remains the
existing Sandboxie driver logging API. SREV-162 records the official Microsoft
kernel error-log DDI shape behind the driver event-log branch:

- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-ioallocateerrorlogentry`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/ns-wdm-_io_error_log_packet`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-iowriteerrorlogentry`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntstrsafe/nf-ntstrsafe-rtlstringcblengtha`

The local logging contract for this path is:

```text
rule allocation failure
  -> WFP_LoadRules
  -> Log_Msg_Process(MSG_1201, session_id, pid)
  -> return FALSE
```

The local fail-closed contract is:

```text
WFP_UpdateProcess
  -> WFP_LoadRules failure
  -> move partially built NewNetFwRules to OldNetFwRules
  -> BlockInternet = TRUE
  -> publish BlockInternet to the WFP process map
  -> WFP_FreeRules(OldNetFwRules)
```

## Boundary

`WFP_LoadRules` owns the concrete rule-load operation and can name the exact
allocation failure. `WFP_UpdateProcess` owns the per-process refresh transition.
Duplicating `MSG_1201` in `WFP_UpdateProcess` would make one allocation failure
produce two popups without adding a more precise state owner.

## Topology

```text
PROCESS + box NetworkAccess settings
  -> WFP_UpdateProcess
  -> WFP_LoadRules(NewNetFwRules, proc)
  -> if NetFw_AllocRule fails:
       WFP_LoadRules logs MSG_1201 with session_id and pid
       returns FALSE with NewNetFwRules possibly partially populated
  -> WFP_UpdateProcess moves NewNetFwRules to OldNetFwRules
  -> BlockInternet = TRUE
  -> WFP process map receives fail-closed state when the process entry exists
  -> WFP_FreeRules(OldNetFwRules)
```

## Logic Risk

The stale TODO made a correct fail-closed path look unfinished and encouraged a
future duplicate popup or a misplaced log in the refresh owner. The risk is not
missing allocation telemetry; it is losing the topology distinction between the
rule-load owner and the policy-refresh owner.

## Fix

The source now replaces the stale `todo: log error` line and typo-heavy
fail-closed comment with a compact SREV-345 contract comment. It states that
`WFP_LoadRules` logs the allocation failure at the rule owner, and that
`WFP_UpdateProcess` owns fail-closed policy plus partial-rule-list cleanup.

No rule parsing, `NetworkAccess` matching, `BlockInternet` behavior,
`BlockLoopback` behavior, spin-lock map update, logging API call, message ID, or
runtime policy decision changed.

## Acceptance Gate

`docs/plan/check-srev-345.py` validates the draft-07 schema, existing
`WFP_LoadRules` allocation-failure log, `WFP_UpdateProcess` fail-closed and
partial-list cleanup order, absence of the stale TODO and typo comment, absence
of a duplicate `MSG_1201` call in `WFP_UpdateProcess`, combined ledger entry,
and split ledger fragment.

Runtime gate: Windows WFP rule-load allocation-failure injection or low-memory
test should show one `MSG_1201` for the concrete allocation failure and the
target process should fail closed with internet blocked while any partially
loaded rule list is freed.
