---
kind: srev-ledger-entry
id: SREV-045
title: Syscall Open Handle Writeback
status: patched-source-level-after-official-probeforwrite-ntclose-and-local-syscall-outp
owner: Sandboxie/core/drv/syscall_open.c
spec: docs/plan/srev-045-syscall-open-handle-writeback.md
schema: docs/plan/srev-045-syscall-open-handle-writeback.schema.json
checker: docs/plan/check-srev-045.py
runtime_gate: invalid/racing output pointer after accepted open/get-next/duplicate does not leak; normal paths still return usable handles and preserve non-zero success statuses
---
### SREV-045: Syscall Open Handle Writeback

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official ProbeForWrite/NtClose and local syscall output-handle ownership analysis; needs Windows invalid-output-handle proof |
| Evidence | The pre-patch finish blocks in `Sandboxie/core/drv/syscall_open.c` wrote restored `NewHandle` values to original user `UserHandlePtr` pointers inside `try/except` in `Syscall_OpenHandle`, `Syscall_GetNextProcess`, and `Syscall_DuplicateHandle`. If writeback raised after the syscall had produced and the driver had accepted `NewHandle`, the function returned `STATUS_PROCESS_IS_TERMINATING` without closing the still driver-owned handle. `Syscall_ReplaceTargetHandle` also probed `UserHandlePtr` with byte alignment for a `HANDLE*` output pointer. |
| Data | Original user `HANDLE*` output pointer, temporary TLS handle slot, restored `NewHandle`, and original syscall status. |
| Schema | `UserHandlePtr` is a user-mode `HANDLE*` output pointer and should be probed with `sizeof(HANDLE)` alignment. `NewHandle` remains driver-owned after TLS restore until writeback succeeds; failed writeback must close it. Successful writeback returns the original syscall status. |
| Topology | Open/get-next/duplicate syscall hooks redirect output handles through a user TLS slot so Sandboxie can inspect the opened object before returning the accepted handle to the caller. |
| Logic Risk | A racing or invalid original output pointer after successful object-open validation can leak the accepted handle because ownership never transfers to the caller. |
| Official Shape | `docs/plan/srev-045-syscall-open-handle-writeback.md` records Microsoft `ProbeForWrite` and `NtClose` references. `docs/plan/srev-045-syscall-open-handle-writeback.schema.json` records the small local restored-handle writeback schema. |
| Fix | `Syscall_WriteRestoredHandleToUser` now owns the restored output boundary for `Syscall_OpenHandle`, `Syscall_GetNextProcess`, and `Syscall_DuplicateHandle`: it probes the `HANDLE*` with handle alignment, writes inside `try/except`, returns `orig_status` on success, and closes `NewHandle` on writeback failure. |
| Acceptance Gate | `docs/plan/check-srev-045.py` validates the schema, helper shape, removal of byte-aligned/direct writeback blocks, and helper routing from all three syscall-open paths; `docs/plan/check-srev-045.sh` is the matrix wrapper. Windows gate: invalid/racing output pointer after accepted open/get-next/duplicate does not leak; normal paths still return usable handles and preserve non-zero success statuses. |
