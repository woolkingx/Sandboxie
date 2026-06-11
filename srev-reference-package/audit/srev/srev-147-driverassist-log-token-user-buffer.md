# SREV-147: DriverAssist Log Token User Buffer

## Stage Gate

| Field | Value |
|---|---|
| Stage | action |
| Input artifact | `Sandboxie/core/svc/DriverAssistLog.cpp`, Microsoft `GetTokenInformation`, `TOKEN_USER`, `LookupAccountSid`, and `SECURITY_MAX_SID_SIZE` references |
| Output artifact | `docs/plan/srev-147-driverassist-log-token-user-buffer.schema.json`, `docs/plan/check-srev-147.py`, `docs/plan/check-srev-147.sh`, ledger fragment |
| Owner | SbieSvc DriverAssist log user-name enrichment helper |
| Acceptance gate | source checker plus full SREV/KPATH/core coverage matrix; Windows service build/runtime proof remains required |

## Evidence

`Sandboxie/core/svc/DriverAssistLog.cpp` became the top unnamed reviewable core
file after SREV-146. `GetUserNameFromProcess` opens the process token through
`SbieApi_QueryProcessInfo(..., 'ptok')`, reads `TokenUser`, translates the SID
with `LookupAccountSid`, and appends `domain\user` to log version 3 messages.

Before this SREV, the helper used `BYTE data[64]` for `GetTokenInformation` and
commented that 44 bytes were needed. That is not the legal API shape:
`TOKEN_USER` carries a SID, and `GetTokenInformation` reports the required byte
length through `ReturnLength`. The helper also wrote terminators at
`user[userSize]` and `domain[domainSize]` after `LookupAccountSid` had mutated
those in/out length variables.

Official references:

- https://learn.microsoft.com/en-us/windows/win32/api/securitybaseapi/nf-securitybaseapi-gettokeninformation
- https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-token_user
- https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-lookupaccountsida
- https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/ns-ntifs-_se_sid

## Data

`GetUserNameFromProcess`, `SbieApi_QueryProcessInfo`, `'ptok'`,
`GetTokenInformation(TokenUser)`, `TOKEN_USER`, `SECURITY_MAX_SID_SIZE`,
`LookupAccountSid`, `user`, `userSize`, `domain`, `domainSize`, and
`LogMessage_Single`.

## Schema

`DRIVERASSIST_LOG_TOKEN_USER_BUFFER` says:

- `GetUserNameFromProcess` owns best-effort user-name enrichment for service log
  messages; failure must not block logging.
- `GetTokenInformation(TokenUser)` writes a variable-size token-user structure
  and reports the required byte count through `ReturnLength`.
- The local TokenUser stack buffer must be sized for `sizeof(TOKEN_USER) +
  SECURITY_MAX_SID_SIZE`, not a historical 64-byte guess.
- `LookupAccountSid` mutates the `userSize` and `domainSize` in/out variables;
  post-call terminators must use the original caller-provided capacities.
- Null or zero-sized caller buffers are invalid and must fail before any write.

## Topology

Legal log enrichment flow:

```text
SbieSvc log message with pid
  -> process token handle from SbieApi_QueryProcessInfo('ptok')
  -> GetTokenInformation(TokenUser) into max-SID-sized local buffer
  -> LookupAccountSid writes bounded user/domain strings
  -> terminators are capped by original caller buffer capacities
  -> LogMessage_Single appends domain\user only on success
```

## Logic Risk

The old fixed 64-byte buffer encoded a local assumption about SID size. If the
TokenUser result exceeds that buffer, user-name enrichment silently fails. The
post-lookup terminator writes also depended on in/out length variables after the
API had modified them, instead of the actual output buffer capacities.

This is log enrichment rather than sandbox policy enforcement. The fix should
keep failure best-effort and should not change log file routing, event-log
routing, or token ownership.

## Fix

`GetUserNameFromProcess` now rejects null or zero-sized output buffers,
initializes both output strings, sizes the TokenUser buffer as
`sizeof(TOKEN_USER) + SECURITY_MAX_SID_SIZE`, preserves original output
capacities, and caps final terminator writes at `capacity - 1`.

## Acceptance Gate

`docs/plan/check-srev-147.py` validates the draft-07 schema, official
references, source buffer shape, output capacity preservation, stale 64-byte
buffer removal, and the ledger fragment. `docs/plan/check-srev-147.sh` is the
matrix wrapper.

Runtime/build gate: Windows service build; log version 3 still appends
`domain\user` for normal user SIDs; a maximal valid SID does not make
`GetTokenInformation(TokenUser)` fail due to the old 64-byte buffer; invalid
or unresolved SIDs keep log writing best-effort without appending a user name.
