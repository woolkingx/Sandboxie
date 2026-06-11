---
kind: srev-ledger-entry
id: SREV-044
title: Token Handle Writeback
status: patched-source-level-after-official-probeforwrite-zwclose-and-local-token-handle
owner: Sandboxie/core/drv/thread_token.c
spec: docs/plan/srev-044-token-handle-writeback.md
schema: docs/plan/srev-044-token-handle-writeback.schema.json
checker: docs/plan/check-srev-044.py
runtime_gate: invalid/racing token output pointer after successful token open does not leak; normal process/thread token opens still return usable handles
---
### SREV-044: Token Handle Writeback

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official ProbeForWrite/ZwClose and local token-handle ownership analysis; needs Windows invalid-output-handle proof |
| Evidence | The pre-patch finish blocks in `Sandboxie/core/drv/thread_token.c` wrote an opened token handle through user `TokenHandle` inside `try/except` in both process-token and thread-token open paths. If the writeback raised after `MyTokenHandle` had been opened, the function returned the exception status without closing the still driver-owned handle. The initial `ProbeForWrite` calls also used byte alignment for a `HANDLE*` output pointer. |
| Data | User `HANDLE*` output pointer and driver-opened process/thread token handle. |
| Schema | `TokenHandle` is a user-mode `HANDLE*` output pointer and should be probed with `sizeof(HANDLE)` alignment. `MyTokenHandle` remains driver-owned until writeback succeeds; failed writeback must close and clear it. |
| Topology | Token-open syscall hooks cross from sandboxed user process arguments into driver-owned token-open logic, then return an opened handle through the user output pointer. |
| Logic Risk | A racing or invalid output pointer after successful token open can leak a token handle because ownership never transfers to the caller. |
| Official Shape | `docs/plan/srev-044-token-handle-writeback.md` records Microsoft `ProbeForWrite` and `ZwClose` references. `docs/plan/srev-044-token-handle-writeback.schema.json` records the small local output-handle ownership schema. |
| Fix | `Thread_WriteTokenHandleToUser` now owns the output boundary for both process-token and thread-token open paths: it probes the `HANDLE*` with handle alignment, writes inside `try/except`, and closes/clears `MyTokenHandle` on writeback failure. |
| Acceptance Gate | `docs/plan/check-srev-044.py` validates the schema, helper shape, removal of byte-aligned/direct writeback blocks, and routing from both token-open common helpers; `docs/plan/check-srev-044.sh` is the matrix wrapper. Windows gate: invalid/racing token output pointer after successful token open does not leak; normal process/thread token opens still return usable handles. |
