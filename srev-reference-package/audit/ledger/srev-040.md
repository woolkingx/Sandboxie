---
kind: srev-ledger-entry
id: SREV-040
title: IsBoxEnabled SID String Boundary
status: patched-source-level-after-official-string-sid-probeforread-shape-analysis-needs
owner: "Sandboxie/core/drv/conf_user.c:601-604"
spec: docs/plan/srev-040-is-box-enabled-sid-string.md
schema: docs/plan/srev-040-is-box-enabled-sid-string.schema.json
checker: docs/plan/check-srev-040.py
runtime_gate: absent SID, valid explicit SID, empty SID, invalid-prefix SID, and overlong unterminated SID
---
### SREV-040: IsBoxEnabled SID String Boundary

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official string-SID/ProbeForRead shape analysis; needs Windows API_IS_BOX_ENABLED explicit-SID proof |
| Evidence | `Sandboxie/core/drv/conf_user.c:601-604` assigned optional `API_IS_BOX_ENABLED_ARGS.sid_string` directly to `sid` and passed the raw user pointer into `Conf_IsBoxEnabled`. `Sandboxie/core/drv/api.c:1043-1055` had an unused `Api_CopySidStringFromUser` helper that copied with `wcsncpy` and could silently truncate an unterminated 96-WCHAR user string into a different local SID string. |
| Data | Optional user-provided `sid_string` and `session_id` passed to `API_IS_BOX_ENABLED`; absent SID uses `Process_GetSidStringAndSessionId` to derive kernel-owned SID/session data. |
| Schema | Optional `sid_string` is a user pointer and must be copied before policy logic reads it. Legal explicit SID input is readable as the existing fixed 96-WCHAR contract, NUL-terminated before the 94-WCHAR local payload cap, non-empty, and starts with `S-`. |
| Topology | The API boundary copies/proves the optional SID string; `Conf_IsBoxEnabled` owns config policy evaluation and must receive only kernel-owned string data or a kernel-derived SID string. |
| Logic Risk | A raw user pointer can be read inside config/user policy evaluation after the API boundary. Overlong unterminated input can be silently truncated, making the policy check evaluate a different SID string than the caller supplied. |
| Official Shape | `docs/plan/srev-040-is-box-enabled-sid-string.md` records Microsoft `ConvertStringSidToSidW` string-SID and `ProbeForRead` references. `docs/plan/srev-040-is-box-enabled-sid-string.schema.json` records the small local API schema. |
| Fix | `Conf_Api_IsBoxEnabled` now copies optional `sid_string` into a local `sidstring[96]` with `Api_CopySidStringFromUser` before calling `Conf_IsBoxEnabled`; `Api_CopySidStringFromUser` now rejects NULL, empty, invalid-prefix, and overlong unterminated input rather than truncating. |
| Acceptance Gate | `docs/plan/check-srev-040.py` validates the schema, official references, SID copy helper shape, and that `Conf_Api_IsBoxEnabled` no longer passes a raw user SID pointer to policy logic; `docs/plan/check-srev-040.sh` is the matrix wrapper. Windows gate: absent SID, valid explicit SID, empty SID, invalid-prefix SID, and overlong unterminated SID. |
