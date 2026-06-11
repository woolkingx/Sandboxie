---
kind: srev-ledger-entry
id: SREV-046
title: Process Query Token Handle
status: patched-source-level-after-official-probeforwrite-ntclose-and-local-process-quer
owner: Sandboxie/core/drv/process_api.c
spec: docs/plan/srev-046-process-query-token-handle.md
schema: docs/plan/srev-046-process-query-token-handle.schema.json
checker: docs/plan/check-srev-046.py
runtime_gate: "`ptok`/`itok`/`ttok` valid, invalid-output, missing-token, and sandboxed-caller-denied cases without handle growth or lock stalls"
---
### SREV-046: Process Query Token Handle

| Field | Content |
|---|---|
| Severity | [blocker] |
| Status | patched source-level after official ProbeForWrite/NtClose and local process-query token ownership analysis; needs Windows invalid-output-handle proof |
| Evidence | The pre-patch `Process_Api_QueryInfo` `ptok` and `itok` paths in `Sandboxie/core/drv/process_api.c` opened token handles and wrote them directly to user `info_data`. If writeback raised after handle open, ownership never transferred and the handle stayed unclosed. The pre-patch `itok` / `ttok` path also wrote user output while `proc->threads_lock` was held at APC_LEVEL, so an exception could skip lock release and IRQL restore. |
| Data | `API_QUERY_PROCESS_INFO` `info_type` values `ptok`, `itok`, and `ttok`; user `ULONG64* info_data`; primary or impersonation token object; opened token handle. |
| Schema | `info_data` is a user-mode `ULONG64*` output pointer written through a try/except helper. Opened token handles remain driver-owned until writeback succeeds; failed writeback closes and clears them. Thread-token lookup under `proc->threads_lock` may only reference the token object or snapshot a boolean; user output and handle creation happen after unlock/lower-IRQL. |
| Topology | Process API query crosses from caller-provided output pointers into driver-owned process/thread token state, then optionally returns a token handle to the caller. |
| Logic Risk | Invalid/racing output after token open can leak token handles, and exceptions while writing under `proc->threads_lock` can skip required lock/IRQL cleanup. |
| Official Shape | `docs/plan/srev-046-process-query-token-handle.md` records Microsoft `ProbeForWrite` and `NtClose` references. `docs/plan/srev-046-process-query-token-handle.schema.json` records the JSON Schema draft-07 local token-query output contract. |
| Fix | `Process_Api_WriteQueryUlong64ToUser` owns `ULONG64*` output writes; `Process_Api_WriteQueryHandleToUser` closes token handles on writeback failure. `ptok` uses the handle helper. `itok` / `ttok` now only snapshots or references token state under `proc->threads_lock`, then releases the lock and lowers IRQL before opening token handles or writing user output. |
| Acceptance Gate | `docs/plan/check-srev-046.py` validates the draft-07 schema, helper shape, direct-write removal, handle-close failure path, and absence of token opening/user output writes while `proc->threads_lock` is held; `docs/plan/check-srev-046.sh` is the matrix wrapper. Windows gate: `ptok`/`itok`/`ttok` valid, invalid-output, missing-token, and sandboxed-caller-denied cases without handle growth or lock stalls. |
