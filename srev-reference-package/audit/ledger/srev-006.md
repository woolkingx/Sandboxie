---
kind: srev-ledger-entry
id: SREV-006
title: Broker Request Fixed Strings Are Used Before NUL-Terminator Proof
status: patched-source-level-for-sbieini-fixed-wchar-arrays-and-service-broker-names-nee
owner: "Sandboxie/core/svc/sbieiniserver.cpp:451-479"
spec: [docs/plan/srev-006a-ini-fixed-string-spec.md, docs/plan/srev-006b-service-name-spec.md]
schema: [docs/plan/srev-006a-ini-fixed-string-spec.schema.json, docs/plan/srev-006b-service-name-spec.schema.json]
checker: [docs/plan/check-srev-006a.sh, docs/plan/check-srev-006b.sh]
runtime_gate: malformed broker strings return invalid-parameter replies without entering INI or SCM calls
---
### SREV-006: Broker Request Fixed Strings Are Used Before NUL-Terminator Proof

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level for SbieIni fixed WCHAR arrays and service broker names; needs Windows malformed broker proof |
| Evidence | Explorer Newton reports `Sandboxie/core/svc/sbieiniserver.cpp:451-479` validates only `value[value_len]` while fixed fields `password[66]`, `section[66]`, and `setting[66]` from `Sandboxie/core/svc/sbieiniwire.h:120-128` flow into C-string APIs. Service names in `Sandboxie/core/svc/servicewire.h:35-40` are length-prefixed but later passed to SCM APIs. |
| Data | Broker request structs with fixed inline WCHAR arrays and length-prefixed service names. |
| Schema | Fixed arrays require an in-bounds NUL before C-string APIs; length-prefixed names require a terminator inside declared bounds or must be copied into a bounded local string. |
| Topology | Untrusted client/broker request data crosses into INI/config and Service Control Manager APIs. |
| Logic Risk | Unterminated or shape-invalid request fields can force out-of-bounds reads in service-side parsing before policy decisions. |
| Official Shape | `docs/plan/srev-006a-ini-fixed-string-spec.md` records Microsoft CRT string routines as null-terminated string APIs. `docs/plan/srev-006b-service-name-spec.md` records `OpenServiceW` service names as null-terminated `LPCWSTR` with a 256-character maximum. |
| Fix | SREV-006A adds bounded terminator gates for consumed SbieIni fixed arrays, routes normal setting mutations through shared setting/value shape helpers, gates `GET_SETTING`, `SET_DAT`, template, and password handlers before C-string use, and tightens variable `value` terminator checks so the terminator must lie inside the message. SREV-006B adds a service-name gate for start/query requests before `OpenServiceW`. |
| Acceptance Gate | `docs/plan/check-srev-006a.sh` proves SbieIni fixed string gates precede authorization, INI, password, template, and dat path logic. `docs/plan/check-srev-006b.sh` proves service-name length and terminator gates precede SCM `OpenServiceW`. Windows gate: malformed broker strings return invalid-parameter replies without entering INI or SCM calls. |
