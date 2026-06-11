---
kind: srev-ledger-entry
id: SREV-251
title: Advapi Change Notify Privilege Filter
status: patched-source-level-after-official-createrestrictedtoken-and-privilege-shape-needs-windows-chrome-runtime-proof
owner: Sandboxie/core/dll/advapi.c
spec: docs/plan/srev-251-advapi-change-notify-privilege-filter.md
schema: docs/plan/srev-251-advapi-change-notify-privilege-filter.schema.json
checker: docs/plan/check-srev-251.py
runtime_gate: Windows build plus Chrome dropped-rights launch smoke proving SeChangeNotifyPrivilege behavior and unchanged restricted-token creation
---

### SREV-251: Advapi Change Notify Privilege Filter

| Field | Content |
|---|---|
| Severity | [moderate] |
| Status | patched source-level after official `CreateRestrictedToken` and privilege shape; needs Windows Chrome runtime proof |
| Evidence | `AdvApi_CreateRestrictedToken` hooks `CreateRestrictedToken` and filters `SE_CHANGE_NOTIFY_NAME` out of the caller's `PrivilegesToDelete` array so Chrome's dropped-rights token keeps traverse-checking bypass semantics. The old code admitted the path as a Chrome 37 dropped-rights hack, ignored the `LookupPrivilegeValueW` result, allocated a scratch `LUID_AND_ATTRIBUTES` array without checking allocation success, and used a nested loop that reused the same `i` variable. |
| Data | `ExistingTokenHandle`, `Flags`, `DeletePrivilegeCount`, `PrivilegesToDelete`, `LUID_AND_ATTRIBUTES`, `LookupPrivilegeValueW`, `SE_CHANGE_NOTIFY_NAME`, `SeChangeNotifyPrivilege`, `pModifiedPrivilegesToDelete`, `CreateRestrictedToken`, and `NewTokenHandle`. |
| Schema | `ADVAPI_CHANGE_NOTIFY_PRIVILEGE_FILTER` says `CreateRestrictedToken` receives a count plus optional array of privileges to delete from the new restricted token; `LookupPrivilegeValueW` resolves `SE_CHANGE_NOTIFY_NAME` to the local LUID used for comparison; `SE_CHANGE_NOTIFY_NAME` is the traverse-checking bypass privilege and is enabled by default for all users; Sandboxie's Chrome compatibility filter may remove only that LUID from the delete list; if lookup or scratch allocation fails, the hook must call the real `CreateRestrictedToken` with the original privilege-delete arguments; this SREV does not change SID disabling, restricted SID handling, token type, returned handle ownership, or Chrome image detection. |
| Topology | Chrome process calls `AdvApi_CreateRestrictedToken`, the hook resolves `SE_CHANGE_NOTIFY_NAME` to a LUID, builds a scratch delete-list without that one LUID, then calls `__sys_CreateRestrictedToken`. Fallback path is lookup failure, scratch allocation failure, or no `SeChangeNotifyPrivilege` in the delete list, in which case original `DeletePrivilegeCount` / `PrivilegesToDelete` pass through unchanged. |
| Logic Risk | The old comment hid a precise token-privilege compatibility rule. The old code also relied on lookup and allocation success without checking either and reused the same loop variable in a nested loop. If allocation failed with a nonzero delete count, the hook could pass a modified count with a null modified array instead of the original Windows arguments. |
| Official Shape | `docs/plan/srev-251-advapi-change-notify-privilege-filter.md` records Microsoft `CreateRestrictedToken`, `LookupPrivilegeValueW`, and privilege-constant references. `docs/plan/srev-251-advapi-change-notify-privilege-filter.schema.json` records the JSON Schema draft-07 local `ADVAPI_CHANGE_NOTIFY_PRIVILEGE_FILTER` contract. |
| Fix | `AdvApi_CreateRestrictedToken` now names the rule as preserving Chrome dropped-rights traverse-checking bypass, checks `DeletePrivilegeCount`, `PrivilegesToDelete`, and `LookupPrivilegeValueW` before filtering, checks the `GlobalAlloc` result before writing the scratch list, uses one loop over the delete list, switches to the modified list only if `SE_CHANGE_NOTIFY_NAME` was found, and otherwise passes the original privilege-delete arguments to `__sys_CreateRestrictedToken`. |
| Acceptance Gate | `docs/plan/check-srev-251.py` validates the draft-07 schema, official reference links, new filter/fallback topology, removal of the stale Chrome 37 hack wording, single-loop source shape, unchanged SID arguments and returned token handle path, and the ledger fragment; `docs/plan/check-srev-251.sh` is the targeted wrapper. Runtime/build gate: Windows build for `advapi.c`; Chrome dropped-rights launch smoke proving `SeChangeNotifyPrivilege` remains available when Chrome requests its deletion; negative smoke where the delete list lacks the privilege and the original list is forwarded unchanged; allocation-failure path is source-gated only unless fault injection is available. |
