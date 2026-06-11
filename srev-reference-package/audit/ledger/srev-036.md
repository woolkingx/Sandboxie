---
kind: srev-ledger-entry
id: SREV-036
title: Config User Name Counted String
status: patched-source-level-after-official-unicode-string-probeforread-string-sid-accou
owner: "Sandboxie/core/drv/conf_user.c:459-502"
spec: docs/plan/srev-036-conf-user-name-wire.md
schema: docs/plan/srev-036-conf-user-name-wire.schema.json
checker: docs/plan/check-srev-036.py
runtime_gate: "normal service username mapping plus odd-length, embedded-NUL, and stale `MaximumLength` malformed inputs fail before persistent `Conf_Users` mutation"
---
### SREV-036: Config User Name Counted String

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official UNICODE_STRING/ProbeForRead/String SID/account-name shape analysis; needs Windows service username runtime proof |
| Evidence | `Sandboxie/core/drv/conf_user.c:459-502` read `sidstring` and `username` `UNICODE_STRING64.Length` with `& ~1`, copied counted bytes into `CONF_USER.space`, then used `wcslen` to derive `sid_len`, `name_len`, and the `name` storage pointer. An embedded NUL in `sidstring` can make `CONF_USER.name` start before the full copied SID bytes end. |
| Data | `API_SET_USER_NAME_ARGS` carries counted `sidstring` and `username` from SbieSvc/DLL into persistent driver `CONF_USER` state. |
| Schema | `UNICODE_STRING64.Length` is bytes, must be WCHAR-aligned, nonzero, within the local 1024-byte cap, and `<= MaximumLength`. Copied counted strings must not contain embedded NUL before deriving local C-string storage. `CONF_USER.sid_len` and `name_len` are WCHAR counts derived from validated byte counts. |
| Topology | SbieSvc validates `msg->sid_string` with `ConvertStringSidToSid`, resolves a username with account lookup/fallback helpers, then calls `SbieApi_SetUserName`; the driver stores the mapping in `Conf_Users` under `Conf_Users_Lock`. |
| Logic Risk | Odd byte lengths can silently truncate. Embedded NUL can make the persistent username overwrite the tail of the copied SID segment or make list matching use a truncated SID string different from the probed payload. |
| Official Shape | `docs/plan/srev-036-conf-user-name-wire.md` records Microsoft `UNICODE_STRING`, `ProbeForRead`, `ConvertStringSidToSidW`, and `LookupAccountSid` references. `docs/plan/srev-036-conf-user-name-wire.schema.json` records the small local driver API schema. |
| Fix | `Conf_Api_SetUserName` now rejects odd byte lengths, validates `Length <= MaximumLength`, scans copied counted segments with `Conf_Api_SetUserNameContainsWChar`, derives SID/name WCHAR counts from byte counts, and places `CONF_USER.name` after the full counted SID plus local trailing NUL. |
| Acceptance Gate | `docs/plan/check-srev-036.py` validates the schema, sender SID-validation evidence, source counted-string guards, copied-buffer NUL rejection, and length derivation; `docs/plan/check-srev-036.sh` is the matrix wrapper. Windows gate: normal service username mapping plus odd-length, embedded-NUL, and stale `MaximumLength` malformed inputs fail before persistent `Conf_Users` mutation. |
