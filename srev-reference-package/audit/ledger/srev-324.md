---
kind: srev-ledger-entry
id: SREV-324
title: RPCRT Disabled UserMgrCli COM Policy Boundary
status: comment-classified-after-official-rpc-compose-and-com-activation-shape-review-no-behavior-change
owner: Sandboxie/core/dll/rpcrt.c
spec: docs/plan/srev-324-rpcrt-disabled-usermgrcli-com-policy-boundary.md
schema: docs/plan/srev-324-rpcrt-disabled-usermgrcli-com-policy-boundary.schema.json
checker: docs/plan/check-srev-324.py
runtime_gate: Explorer context menu smoke with the WindowsExplorer template on and off, proving Pin To Start Screen remains denied by ClosedClsid while the disabled UserMgrCli RPC block remains inactive
---
### SREV-324: RPCRT Disabled UserMgrCli COM Policy Boundary

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | comment classified after official RPC compose and COM activation shape review; no source behavior change |
| Evidence | `RpcRt_RpcStringBindingComposeW` actively rewrites SPP callers to `SPPCTransportEndpoint-00001` and then forwards to `__sys_RpcStringBindingComposeW`. The adjacent `UUID_UserMgrCli` / `STATUS_ACCESS_DENIED` branch is disabled source. The active Pin To Start Screen policy is `Sandboxie/install/Templates.ini` `ClosedClsid={470C0EBD-5D73-4D58-9CED-E91E22E23282}` loaded by `Com_IsClosedClsid` and enforced before COM class activation. `IContextMenuClsid` is a separate post-creation Shell interface hook. |
| Data | `RpcRt_RpcStringBindingComposeW`, `UUID_UserMgrCli`, disabled `ObjUuid` deny branch, `SPPCTransportEndpoint-00001`, `__sys_RpcStringBindingComposeW`, `ClosedClsid`, Pin To Start Screen CLSID `{470C0EBD-5D73-4D58-9CED-E91E22E23282}`, `Com_IsClosedClsid`, `Com_CoCreateInstance`, `IContextMenuClsid`, and `SH32_IContextMenu_Hook`. |
| Schema | `RPCRT_DISABLED_USERMGRCLI_COM_POLICY_BOUNDARY` says official `RpcStringBindingComposeW` owns RPC string-binding composition, not COM class policy; `RpcRt_RpcStringBindingComposeW` owns the local SPP endpoint rewrite before native forwarding; the UserMgrCli branch in `rpcrt.c` remains disabled historical source; Pin To Start Screen blocking is owned by COM `ClosedClsid` loaded from templates/settings and enforced through `Com_IsClosedClsid` before COM class activation; `IContextMenuClsid` is a separate post-creation Shell interface hook; this SREV changes comments and proof only. |
| Topology | `RPC caller -> RpcRt_RpcStringBindingComposeW -> optional SPP endpoint rewrite -> __sys_RpcStringBindingComposeW`. Active Pin To Start Screen policy is `WindowsExplorer template -> ClosedClsid -> Com_LoadClsidList -> Com_IsClosedClsid -> CoGetClassObject / CoCreateInstance / CoCreateInstanceEx deny gate`. Context menu interface interception is `CoCreateInstance success in Explorer -> IID_IContextMenu -> SH32_IContextMenu_Hook -> IContextMenuClsid`. |
| Logic Risk | The old `rpcrt.c` comment mixed RPC string-binding composition, COM class activation denial, and Shell context menu interface hooking. Because the UserMgrCli branch is disabled, that wording could lead a future patch to reactivate an RPC object-UUID deny as if it were the active COM policy, moving a COM class decision into the RPC string compose hook and bypassing the template-owned `ClosedClsid` contract. |
| Official Shape | `docs/plan/srev-324-rpcrt-disabled-usermgrcli-com-policy-boundary.md` records Microsoft `RpcStringBindingComposeW`, `CoCreateInstance`, context menu handler, and `IContextMenu` references. `docs/plan/srev-324-rpcrt-disabled-usermgrcli-com-policy-boundary.schema.json` records the JSON Schema draft-07 local `RPCRT_DISABLED_USERMGRCLI_COM_POLICY_BOUNDARY` contract. |
| Fix | Comment-only source clarification. The `rpcrt.c` note now says SREV-324 keeps the UserMgrCli RPC block inactive and that Pin To Start Screen is a COM `ClosedClsid`/template policy, not an RPC compose policy. No predicate, endpoint rewrite, disabled branch, COM class policy, template setting, context menu hook, native RPC forwarding, or native COM forwarding behavior changed. |
| Acceptance Gate | `docs/plan/check-srev-324.py` validates the draft-07 schema, official references, source comment, inactive UserMgrCli branch, active SPP rewrite, native `RpcStringBindingComposeW` forwarding, `Templates.ini` Pin To Start Screen `ClosedClsid`, `Com_IsClosedClsid` enforcement before COM activation, separate `IContextMenuClsid` hook path, stale Explorer hang wording removal, combined ledger entry, and split ledger fragment; `docs/plan/check-srev-324.sh` is the targeted wrapper. Windows gate: Explorer context menu smoke with the WindowsExplorer template on and off, proving Pin To Start Screen remains denied by `ClosedClsid` while the disabled UserMgrCli RPC block remains inactive. |
