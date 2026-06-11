# SREV-344: WFP Transaction Abort Cleanup

| Field | Content |
|---|---|
| Stage | schema -> topology -> action -> verify |
| Input artifact | `Sandboxie/core/drv/wfp.c`, Microsoft `FwpmTransactionAbort0`, `FwpmTransactionBegin0`, `FwpmTransactionCommit0`, `FwpmEngineOpen0`, `FwpmEngineClose0`, `FWPM_SESSION0`, and WFP Object Management documentation |
| Output artifact | Source patch, draft-07 schema, checker, and ledger fragment |
| Owner | `WFP_Install_Callbacks` failed-install transaction/session cleanup path |
| Acceptance gate | Targeted checker validates official references, abort status capture, close-session fallback edge, stale potential-leak wording removal, dynamic-session topology, and ledger fragment |

## Data

`WFP_Install_Callbacks` opens a dynamic WFP filter-engine session, begins a
transaction, registers a sublayer and four callouts/filters, and commits the
transaction. On any failure after transaction begin it takes the `Exit` path.

Before this SREV, the failure path called `FwpmTransactionAbort` when
`in_transaction == TRUE`, then immediately used `_Analysis_assume_lock_not_held_`
with a comment saying there was a potential leak if `FwpmTransactionAbort`
failed. The abort status was not captured or logged. The function then
unregistered callouts that had reached the driver registration stage and closed
`WFP_engine_handle`.

## Official Shape

Microsoft documents `FwpmTransactionBegin0` as beginning an explicit
transaction in the current session, and `FwpmTransactionCommit0` as committing
the current transaction. `FwpmTransactionAbort0` aborts and rolls back the
current transaction, can only be called from within a transaction, and returns
WFP/RPC/other NTSTATUS errors.

Microsoft documents `FwpmEngineOpen0` as opening a session to the filter engine,
with `FWPM_SESSION_FLAG_DYNAMIC` causing objects added during the session to be
deleted automatically when the session ends. `FwpmEngineClose0` closes the open
session. WFP Object Management documents that when a session is destroyed, BFE
first aborts any existing transaction, and objects added during a dynamic
session are removed when the session ends.

Official references:

- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/fwpmk/nf-fwpmk-fwpmtransactionbegin0`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/fwpmk/nf-fwpmk-fwpmtransactioncommit0`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/fwpmk/nf-fwpmk-fwpmtransactionabort0`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/fwpmk/nf-fwpmk-fwpmengineopen0`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/fwpmk/nf-fwpmk-fwpmengineclose0`
- `https://learn.microsoft.com/en-us/windows/desktop/api/fwpmtypes/ns-fwpmtypes-fwpm_session0`
- `https://learn.microsoft.com/vi-vn/windows/win32/fwp/object-management`

## Boundary

```text
WFP_Install_Callbacks
  -> FwpmEngineOpen(dynamic session)
  -> FwpmTransactionBegin
  -> WFP_RegisterSubLayer / WFP_RegisterCallout
  -> FwpmTransactionCommit
  -> failure while in_transaction
  -> FwpmTransactionAbort status
  -> optional abort failure log
  -> callout unregister cleanup
  -> FwpmEngineClose dynamic-session cleanup
```

`FwpmTransactionAbort` owns the explicit rollback edge. `FwpmEngineClose` owns
the final session cleanup edge. The local function owns observing abort failure
without stopping close-session cleanup.

## Topology

```text
FWPM_SESSION_FLAG_DYNAMIC
  -> FwpmEngineOpen
  -> WFP_engine_handle
  -> FwpmTransactionBegin
  -> in_transaction = TRUE
  -> install sublayer/callouts/filters
  -> if commit succeeds: in_transaction = FALSE
  -> if failure and in_transaction:
       abort_status = FwpmTransactionAbort(WFP_engine_handle)
       static-analysis lock assumption remains paired with abort edge
       if abort failed: DbgPrint status
  -> unregister any registered callouts
  -> FwpmEngineClose(WFP_engine_handle)
  -> WFP_engine_handle = NULL
```

## Logic Risk

The old comment correctly hinted that abort failure matters, but it attached the
risk to a static-analysis annotation and discarded the only runtime evidence:
the abort return status. If BFE/RPC reports abort failure, later diagnostics need
that status while the cleanup path still closes the dynamic session to let BFE
own final transaction/session teardown.

## Fix

`WFP_Install_Callbacks` now captures `FwpmTransactionAbort` into
`abort_status`, keeps `_Analysis_assume_lock_not_held_` immediately after the
abort edge, and logs abort failure before continuing to callout unregister and
`FwpmEngineClose`. No transaction begin/commit order, dynamic-session flag,
registration order, callout unregister order, engine-close behavior, or success
path changed.

## Acceptance Gate

`docs/plan/check-srev-344.py` validates the draft-07 schema, official
references, dynamic session flag, transaction begin/commit state transitions,
abort status capture, abort failure logging, `_Analysis_assume_lock_not_held_`
placement, callout unregister cleanup, engine close cleanup, stale potential
leak wording removal, combined ledger entry, and split ledger fragment.

Runtime gate: Windows WFP failure-injection matrix for sublayer/callout/filter
registration failures after transaction begin, `FwpmTransactionAbort` success
and failure, BFE/RPC shutdown during install, dynamic-session cleanup,
Driver Verifier, and repeated WFP enable/disable cycles with no leaked WFP
objects or callouts.
