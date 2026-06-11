---
kind: srev-ledger-entry
id: SREV-344
title: WFP Transaction Abort Cleanup
status: patched-source-level-after-official-wfp-transaction-session-cleanup-review-needs-windows-runtime-proof
owner: Sandboxie/core/drv/wfp.c
spec: docs/plan/srev-344-wfp-transaction-abort-cleanup.md
schema: docs/plan/srev-344-wfp-transaction-abort-cleanup.schema.json
checker: docs/plan/check-srev-344.py
runtime_gate: Windows WFP failure-injection matrix for transaction abort success failure BFE RPC shutdown dynamic session cleanup Driver Verifier and repeated enable disable cycles
---

### SREV-344: WFP Transaction Abort Cleanup

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | patched source-level after official WFP transaction/session cleanup review; needs Windows runtime proof |
| Evidence | `WFP_Install_Callbacks` opens a dynamic WFP engine session, begins a transaction, registers a sublayer plus send/receive callouts and filters, commits the transaction, and exits on intermediate errors. The old failure path called `FwpmTransactionAbort(WFP_engine_handle)` when `in_transaction` was true but discarded the abort status and carried an inline comment warning about a potential leak if abort failed. The path then unregistered callouts and closed `WFP_engine_handle`. |
| Data | `WFP_Install_Callbacks`, `FWPM_SESSION_FLAG_DYNAMIC`, `WFP_engine_handle`, `FwpmEngineOpen`, `FwpmTransactionBegin`, `in_transaction`, `WFP_RegisterSubLayer`, `WFP_RegisterCallout`, `FwpmTransactionCommit`, `FwpmTransactionAbort`, `abort_status`, `_Analysis_assume_lock_not_held_`, `FwpsCalloutUnregisterById`, `FwpmEngineClose`, and `WFP_engine_handle = NULL`. |
| Schema | `WFP_TRANSACTION_ABORT_CLEANUP` says `WFP_Install_Callbacks` owns failed-install cleanup for the dynamic WFP engine session; `FwpmTransactionAbort` is the explicit rollback edge when `in_transaction` is true; `FwpmEngineClose` is the final dynamic-session cleanup edge even if abort reports an error; abort status must be captured and logged before continuing cleanup; `_Analysis_assume_lock_not_held_` stays paired with the abort edge for static analysis; callout unregister cleanup remains separate from filter-engine session cleanup; Windows runtime proof is still required for BFE/RPC abort-failure behavior. |
| Topology | `FWPM_SESSION_FLAG_DYNAMIC -> FwpmEngineOpen -> WFP_engine_handle -> FwpmTransactionBegin -> in_transaction = TRUE -> install sublayer/callouts/filters -> commit success clears in_transaction; failure while in_transaction -> abort_status = FwpmTransactionAbort -> static-analysis lock assumption -> optional abort failure DbgPrint -> unregister registered callouts -> FwpmEngineClose -> WFP_engine_handle = NULL`. |
| Logic Risk | The old comment correctly hinted that abort failure matters, but it attached the risk to a static-analysis annotation and discarded the only runtime evidence: the abort return status. If BFE/RPC reports abort failure, later diagnostics need that status while the cleanup path still closes the dynamic session to let BFE own final transaction/session teardown. |
| Official Shape | Microsoft documents `FwpmTransactionBegin0`, `FwpmTransactionCommit0`, and `FwpmTransactionAbort0` as explicit transaction controls; abort can only be called within a transaction and returns WFP/RPC/other NTSTATUS errors. Microsoft documents `FwpmEngineOpen0`/`FwpmEngineClose0` as session open/close. `FWPM_SESSION_FLAG_DYNAMIC` removes objects added during the session when the session ends. WFP Object Management says BFE aborts any existing transaction when a session is destroyed. |
| Fix | `WFP_Install_Callbacks` now captures `FwpmTransactionAbort` into `abort_status`, keeps `_Analysis_assume_lock_not_held_` immediately after the abort edge, and logs abort failure before continuing to callout unregister and `FwpmEngineClose`. No transaction begin/commit order, dynamic-session flag, registration order, callout unregister order, engine-close behavior, or success path changed. |
| Acceptance Gate | `docs/plan/check-srev-344.py` validates the draft-07 schema, official references, dynamic session flag, transaction begin/commit state transitions, abort status capture, abort failure logging, `_Analysis_assume_lock_not_held_` placement, callout unregister cleanup, engine close cleanup, stale potential leak wording removal, combined ledger entry, and split ledger fragment; `docs/plan/check-srev-344.sh` is the targeted wrapper. Runtime gate: Windows WFP failure-injection matrix for sublayer/callout/filter registration failures after transaction begin, `FwpmTransactionAbort` success and failure, BFE/RPC shutdown during install, dynamic-session cleanup, Driver Verifier, and repeated WFP enable/disable cycles with no leaked WFP objects or callouts. |
