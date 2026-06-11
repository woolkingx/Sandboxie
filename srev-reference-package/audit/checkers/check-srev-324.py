#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-324 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-324 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-324-rpcrt-disabled-usermgrcli-com-policy-boundary.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-324 failed: schema is not draft-07")
if schema.get("id") != "RPCRT_DISABLED_USERMGRCLI_COM_POLICY_BOUNDARY":
    raise SystemExit("SREV-324 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/dll/rpcrt.c":
    raise SystemExit("SREV-324 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "official RpcStringBindingComposeW owns RPC string-binding composition",
    "local SPP endpoint rewrite",
    "UserMgrCli branch in rpcrt.c remains disabled historical source",
    "Pin To Start Screen blocking is owned by COM ClosedClsid",
    "IContextMenuClsid is a separate post-creation Shell interface hook",
    "changes comments and proof only",
]:
    require(contracts, term, "schema contracts")

rpcrt = (ROOT / "Sandboxie/core/dll/rpcrt.c").read_text()
com = (ROOT / "Sandboxie/core/dll/com.c").read_text()
sh = (ROOT / "Sandboxie/core/dll/sh.c").read_text()
templates = (ROOT / "Sandboxie/install/Templates.ini").read_text()
settings = (ROOT / "Sandboxie/install/SbieSettings.ini").read_text()
spec = (ROOT / "docs/plan/srev-324-rpcrt-disabled-usermgrcli-com-policy-boundary.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-324.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

start = rpcrt.index("RPC_STATUS RPC_ENTRY RpcRt_RpcStringBindingComposeW(")
end = rpcrt.index("// RpcRt_RpcBindingCopy", start)
compose_func = rpcrt[start:end]

for term in [
    "SREV-324: keep the UserMgrCli RPC block inactive here.",
    "Pin To Start Screen is a COM ClosedClsid/template policy, not an RPC compose policy.",
    "EndPoint = L\"SPPCTransportEndpoint-00001\";",
    "Scm_Start_Sppsvc();",
    "return __sys_RpcStringBindingComposeW(ObjUuid,ProtSeq,NetworkAddr,EndPoint,Options,StringBinding);",
    "//else if (ObjUuid && (!_wcsicmp(ObjUuid, UUID_UserMgrCli)))",
    "//    return STATUS_ACCESS_DENIED;",
]:
    require(compose_func, term, "RpcStringBindingComposeW source")

for line in compose_func.splitlines():
    if line.lstrip().startswith("else if (ObjUuid && (!_wcsicmp(ObjUuid, UUID_UserMgrCli)))"):
        raise SystemExit("SREV-324 failed: disabled UserMgrCli branch appears active")

spp = compose_func.index("EndPoint = L\"SPPCTransportEndpoint-00001\";")
native = compose_func.index("return __sys_RpcStringBindingComposeW")
if not spp < native:
    raise SystemExit("SREV-324 failed: SPP rewrite must remain before native forwarding")

for stale in [
    "we must block this in Win 10",
    "r-click context menu hang in Explorer",
    "this breaks other things",
    "inside Com_CoCreateInstance",
]:
    reject(compose_func, stale, "RpcStringBindingComposeW UserMgrCli comment")

for term in [
    "ClosedClsid={470C0EBD-5D73-4D58-9CED-E91E22E23282}",
    "[Template_WindowsExplorer]",
    "# prevent context menu hang",
]:
    require(templates, term, "Templates.ini Pin To Start Screen policy")

for term in [
    "[ClosedClsid]",
    "Description=Blocks COM class identifiers (CLSIDs) from being accessed by sandboxed programs.",
    "[IContextMenuClsid]",
]:
    require(settings, term, "SbieSettings.ini setting docs")

for term in [
    "_FX BOOLEAN Com_IsClosedClsid(REFCLSID rclsid)",
    "static const WCHAR* setting = L\"ClosedClsid\";",
    "Com_LoadClsidList(setting, &Com_ClosedClsids, &Com_NumClosedClsids, NULL);",
    "if (Com_IsClosedClsid(rclsid))",
    "return E_ACCESSDENIED;",
    "hr = __sys_CoCreateInstance(rclsid, pUnkOuter, clsctx, riid, ppv);",
]:
    require(com, term, "COM ClosedClsid source")

closed_gate = com.index("if (Com_IsClosedClsid(rclsid))", com.index("_FX HRESULT Com_CoCreateInstance("))
native_com = com.index("hr = __sys_CoCreateInstance(rclsid, pUnkOuter, clsctx, riid, ppv);", closed_gate)
if not closed_gate < native_com:
    raise SystemExit("SREV-324 failed: ClosedClsid gate must precede native CoCreateInstance")

for term in [
    "memcmp(riid, &IID_IContextMenu, sizeof(GUID)) == 0",
    "SH32_IContextMenu_Hook(rclsid, *ppv);",
]:
    require(com, term, "COM IContextMenu hook dispatch")

for term in [
    "SbieApi_QueryConfAsIs(\n                NULL, L\"IContextMenuClsid\"",
    "SH32_IContextMenuHook_QueryInterface",
]:
    require(sh, term, "Shell IContextMenu hook")

for term in [
    "RPCRT_DISABLED_USERMGRCLI_COM_POLICY_BOUNDARY",
    "Pin To Start Screen is a COM",
    "UserMgrCli RPC block inactive",
    "No predicate, endpoint rewrite, disabled branch, COM class policy",
]:
    require(spec, term, "spec")

for term in [
    "kind: srev-ledger-entry",
    "id: SREV-324",
    "owner: Sandboxie/core/dll/rpcrt.c",
    "spec: docs/plan/srev-324-rpcrt-disabled-usermgrcli-com-policy-boundary.md",
    "schema: docs/plan/srev-324-rpcrt-disabled-usermgrcli-com-policy-boundary.schema.json",
    "checker: docs/plan/check-srev-324.py",
]:
    require(ledger_fragment, term, "ledger fragment header")

for term in [
    "### SREV-324: RPCRT Disabled UserMgrCli COM Policy Boundary",
    "RPCRT_DISABLED_USERMGRCLI_COM_POLICY_BOUNDARY",
    "RpcStringBindingComposeW",
    "ClosedClsid",
    "IContextMenuClsid",
]:
    require(ledger, term, "combined ledger")

print("SREV-324 schema/source gate passed")
