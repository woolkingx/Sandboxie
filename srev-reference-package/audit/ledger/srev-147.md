---
kind: srev-ledger-entry
id: SREV-147
title: DriverAssist Log Token User Buffer
status: patched-source-level-after-official-token-user-api-review-needs-windows-runtime-proof
owner: Sandboxie/core/svc/DriverAssistLog.cpp
spec: docs/plan/srev-147-driverassist-log-token-user-buffer.md
schema: docs/plan/srev-147-driverassist-log-token-user-buffer.schema.json
checker: docs/plan/check-srev-147.py
runtime_gate: Windows service build and log version 3 domain/user runtime proof
---

### SREV-147: DriverAssist Log Token User Buffer

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | patched source-level after official GetTokenInformation, TOKEN_USER, LookupAccountSid, and SECURITY_MAX_SID_SIZE review; needs Windows service runtime proof |
| Evidence | `Sandboxie/core/svc/DriverAssistLog.cpp` was the top unnamed reviewable core file after SREV-146. `GetUserNameFromProcess` uses `SbieApi_QueryProcessInfo(..., 'ptok')`, `GetTokenInformation(TokenUser)`, and `LookupAccountSid` to append `domain\user` to log version 3 messages. Before this SREV, the TokenUser storage was `BYTE data[64]` with a historical 44-byte comment, and post-lookup terminators were written at `user[userSize]` / `domain[domainSize]` after the API had mutated those in/out length variables. |
| Data | `GetUserNameFromProcess`, `SbieApi_QueryProcessInfo`, `'ptok'`, `GetTokenInformation(TokenUser)`, `TOKEN_USER`, `SECURITY_MAX_SID_SIZE`, `LookupAccountSid`, `user`, `userSize`, `domain`, `domainSize`, and `LogMessage_Single`. |
| Schema | `DRIVERASSIST_LOG_TOKEN_USER_BUFFER` says `GetUserNameFromProcess` owns best-effort user-name enrichment for service log messages; `GetTokenInformation(TokenUser)` writes variable-size token-user data and reports required bytes through `ReturnLength`; the local TokenUser buffer must be sized for `sizeof(TOKEN_USER) + SECURITY_MAX_SID_SIZE`; `LookupAccountSid` mutates the size variables, so post-call terminators must use the original capacities; null or zero-sized output buffers fail before writes. |
| Topology | Legal flow is log message with pid, token handle from `SbieApi_QueryProcessInfo('ptok')`, TokenUser read into a max-SID-sized buffer, `LookupAccountSid` writes bounded user/domain strings, terminators capped by original capacities, then `LogMessage_Single` appends `domain\user` only on success. |
| Logic Risk | The old 64-byte TokenUser buffer encoded a SID-size assumption and can fail on larger valid SIDs. The old terminator writes depended on mutated in/out length variables instead of actual caller buffer capacities. This affects log enrichment, not sandbox policy. |
| Official Shape | `docs/plan/srev-147-driverassist-log-token-user-buffer.md` records Microsoft `GetTokenInformation`, `TOKEN_USER`, `LookupAccountSid`, and `SECURITY_MAX_SID_SIZE` references. `docs/plan/srev-147-driverassist-log-token-user-buffer.schema.json` records the JSON Schema draft-07 local `DRIVERASSIST_LOG_TOKEN_USER_BUFFER` contract. |
| Fix | `GetUserNameFromProcess` now rejects invalid output buffers, initializes outputs, preserves original capacities, uses `BYTE data[sizeof(TOKEN_USER) + SECURITY_MAX_SID_SIZE]`, and caps final terminator writes at `capacity - 1`. |
| Acceptance Gate | `docs/plan/check-srev-147.py` validates the draft-07 schema, official references, source buffer shape, output capacity preservation, stale 64-byte buffer removal, log version 3 preservation, and the ledger fragment; `docs/plan/check-srev-147.sh` is the matrix wrapper. Runtime/build gate: Windows service build; log version 3 still appends `domain\user` for normal user SIDs; a maximal valid SID does not fail due to the old 64-byte buffer; unresolved SIDs keep logging best-effort without appending a user name. |
