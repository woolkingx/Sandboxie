---
kind: srev-ledger-entry
id: SREV-042
title: Box Name Helper Routing
status: patched-source-level-after-srev-041-box-name-schema-analysis-needs-windows-force
owner: "Sandboxie/core/drv/session.c:533-538"
spec: docs/plan/srev-042-box-name-helper-routing.md
schema: docs/plan/srev-042-box-name-helper-routing.schema.json
checker: docs/plan/check-srev-042.py
runtime_gate: ForceChildren and Process_Api_Enum with valid, empty, invalid-character, and overlong unterminated explicit box names
---
### SREV-042: Box Name Helper Routing

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after SREV-041 box-name schema analysis; needs Windows ForceChildren/Process_Api_Enum malformed-box-name proof |
| Evidence | `Sandboxie/core/drv/session.c:533-538` and `Sandboxie/core/drv/process_api.c:1082-1085` still duplicated the pre-SREV-041 box-name copy pattern: probe `(BOXNAME_COUNT - 2)` WCHARs, then `wcsncpy` into a zeroed local buffer. |
| Data | Explicit user box-name pointers passed to `Session_Api_ForceChildren` and `Process_Api_Enum`. |
| Schema | Explicit user box names must route through `Api_CopyBoxNameFromUser`, the local fixed-string schema owner from SREV-041. The old local duplicate `ProbeForRead + wcsncpy` copy shape is illegal because it preserves silent truncation. |
| Topology | Session force-child state and process enumeration should receive only validated local box-name identity; process-owned box names remain trusted local state when `Process_Api_Enum` is called with `proc`. |
| Logic Risk | Overlong unterminated input can be truncated into a different box identity before force-child insertion or process enumeration filtering. |
| Official Shape | `docs/plan/srev-042-box-name-helper-routing.md` records Microsoft `ProbeForRead` and links the local SREV-041 box-name schema. `docs/plan/srev-042-box-name-helper-routing.schema.json` records the routing schema. |
| Fix | `Session_Api_ForceChildren` and `Process_Api_Enum` now call `Api_CopyBoxNameFromUser` for explicit user box names and reject invalid names before mutating/session or enumeration logic. |
| Acceptance Gate | `docs/plan/check-srev-042.py` validates helper routing and rejects the old duplicate `ProbeForRead + wcsncpy` pattern in both API paths; `docs/plan/check-srev-042.sh` is the matrix wrapper. Windows gate: ForceChildren and Process_Api_Enum with valid, empty, invalid-character, and overlong unterminated explicit box names. |
