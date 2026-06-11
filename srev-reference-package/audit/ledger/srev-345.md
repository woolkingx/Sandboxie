---
kind: srev-ledger-entry
id: SREV-345
title: WFP Rule Load Fail-Closed Logging Boundary
status: patched-comment-topology-no-behavior-change-needs-windows-runtime-injection-proof
owner: Sandboxie/core/drv/wfp.c
spec: docs/plan/srev-345-wfp-rule-load-fail-closed-logging.md
schema: docs/plan/srev-345-wfp-rule-load-fail-closed-logging.schema.json
checker: docs/plan/check-srev-345.py
runtime_gate: Windows WFP rule-load allocation-failure injection or low-memory test proves one MSG_1201 and fail-closed internet blocking with partial rule list cleanup
---

### SREV-345: WFP Rule Load Fail-Closed Logging Boundary

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | patched comment/topology after WFP rule-load logging owner review; no behavior change; needs Windows runtime injection proof |
| Evidence | `WFP_UpdateProcess` calls `WFP_LoadRules(&NewNetFwRules, proc)` when internet access is not already blocked by `AllowNetworkAccess`. `WFP_LoadRules` walks matching `NetworkAccess` settings, allocates each `NETFW_RULE`, parses it, and appends it to the caller-provided list. Its only current false path is `NetFw_AllocRule` failure, which already logs `MSG_1201` with `proc->box->session_id` and `proc->pid`. `WFP_UpdateProcess` then moves any partially built `NewNetFwRules` into `OldNetFwRules`, sets `BlockInternet = TRUE`, publishes that state when the process map entry exists, and frees `OldNetFwRules`. The old update-path comment said `todo: log error`. |
| Data | `WFP_LoadRules`, `WFP_UpdateProcess`, `NetworkAccess`, `Process_MatchImageAndGetValue`, `NetFw_AllocRule`, `NETFW_RULE`, `NetFw_ParseRule`, `NetFw_AddRule`, `Log_Msg_Process`, `MSG_1201`, `NewNetFwRules`, `OldNetFwRules`, `BlockInternet`, `wfp_proc->BlockInternet`, and `WFP_FreeRules`. |
| Schema | `WFP_RULE_LOAD_FAIL_CLOSED_LOGGING` says `WFP_LoadRules` owns `NetworkAccess` rule construction and concrete allocation-failure logging; `NetFw_AllocRule` failure logs `MSG_1201` with process session id and pid before `WFP_LoadRules` returns false; `WFP_UpdateProcess` owns the fail-closed transition and must not duplicate the `MSG_1201` popup for the same allocation failure; partially loaded `NewNetFwRules` move to `OldNetFwRules` before cleanup; `BlockInternet = TRUE` is the local fail-closed state for rule-load failure; this SREV changes comments and proof only. |
| Topology | `PROCESS + box NetworkAccess settings -> WFP_UpdateProcess -> WFP_LoadRules(NewNetFwRules, proc) -> NetFw_AllocRule failure -> Log_Msg_Process(MSG_1201, session_id, pid) -> false return -> WFP_UpdateProcess moves NewNetFwRules to OldNetFwRules -> BlockInternet = TRUE -> WFP process map receives fail-closed state when present -> WFP_FreeRules(OldNetFwRules)`. |
| Logic Risk | The stale TODO made a correct fail-closed path look unfinished and encouraged a future duplicate popup or misplaced refresh-layer log. The missing artifact was the owner/topology contract, not another copy of the allocation-failure log. |
| Official Shape | No new Windows API edge is introduced by this SREV. The logging sink remains the existing Sandboxie driver logging API; SREV-162 records the official Microsoft kernel error-log DDI shape behind the event-log branch. |
| Fix | The source now replaces the stale `todo: log error` line and typo-heavy fail-closed comment with a compact SREV-345 contract comment. It states that `WFP_LoadRules` logs the allocation failure at the rule owner, and that `WFP_UpdateProcess` owns fail-closed policy plus partial-rule-list cleanup. No rule parsing, `NetworkAccess` matching, `BlockInternet` behavior, `BlockLoopback` behavior, spin-lock map update, logging API call, message ID, or runtime policy decision changed. |
| Acceptance Gate | `docs/plan/check-srev-345.py` validates the draft-07 schema, existing `WFP_LoadRules` allocation-failure log, `WFP_UpdateProcess` fail-closed and partial-list cleanup order, absence of the stale TODO and typo comment, absence of a duplicate `MSG_1201` call in `WFP_UpdateProcess`, combined ledger entry, and split ledger fragment; `docs/plan/check-srev-345.sh` is the targeted wrapper. Runtime gate: Windows WFP rule-load allocation-failure injection or low-memory test should show one `MSG_1201` for the concrete allocation failure and the target process should fail closed with internet blocked while any partially loaded rule list is freed. |
