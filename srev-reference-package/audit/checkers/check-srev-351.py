#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-351 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-351 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-351-gui-dde-service-proxy-topology-comment.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-351 failed: schema is not draft-07")
if schema.get("id") != "GUI_DDE_SERVICE_PROXY_TOPOLOGY_COMMENT":
    raise SystemExit("SREV-351 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/svc/GuiServer.cpp":
    raise SystemExit("SREV-351 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "DdeProxyThreadSlave owns the SbieSvc service-side DDE proxy window and transport edge",
    "guidde.c owns the sandbox-side DDE hook and posted-DDE reconstruction topology",
    "private win32k and integrity-level observations are evidence not API contract",
    "the legal protocol shape remains documented DDE messages and DDE lParam helpers",
    "WM_COPYDATA is a SendMessage-only copy boundary whose data is valid only during message processing",
    "SREV-084 owns DDE ACK lParam forwarding behavior",
    "SREV-347 owns direct WM_DDE_ACK proxy startup and client HWND validation",
    "SREV-348 owns DDE request/data route mapping",
    "this SREV changes comments and proof only",
]:
    require(contracts, term, "schema")

svc = (ROOT / "Sandboxie/core/svc/GuiServer.cpp").read_text()
guidde = (ROOT / "Sandboxie/core/dll/guidde.c").read_text()
spec = (ROOT / "docs/plan/srev-351-gui-dde-service-proxy-topology-comment.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-351.md").read_text()
srev_084 = (ROOT / "docs/plan/ledger/srev-084.md").read_text()
srev_293 = (ROOT / "docs/plan/ledger/srev-293.md").read_text()
srev_347 = (ROOT / "docs/plan/ledger/srev-347.md").read_text()
srev_348 = (ROOT / "docs/plan/ledger/srev-348.md").read_text()

proxy_start = svc.index("ULONG GuiServer::DdeProxyThreadSlave(")
proxy_end = svc.index("//---------------------------------------------------------------------------\n// KillJob", proxy_start)
proxy_block = svc[proxy_start:proxy_end]

comment_end = proxy_block.index("static ATOM _atom = 0;")
comment = proxy_block[:comment_end]

for term in [
    "SREV-351: this service-side proxy is the out-of-sandbox transport",
    "restricted-token posted-DDE topology described in",
    "core/dll/guidde.c",
    "To the real client it is the server; to the",
    "sandboxed server it is the client.",
    "The sandboxed side posts DDE EXECUTE/REQUEST messages to this proxy",
    "The proxy copies those payloads to the sandbox server through",
    "WM_COPYDATA because WM_COPYDATA data is valid only during SendMessage",
    "and must be copied before later use.",
]:
    require(comment, term, "DdeProxyThreadSlave topology comment")

for stale in [
    "IL bug in core/dll/guidde.c",
    "not subject to",
    "that IL bug",
    "work around the IL bug",
    "global variable hack",
]:
    reject(comment, stale, "DdeProxyThreadSlave topology comment")

for term in [
    "SANDBOXIE L\"_DDE_ProxyClass2\"",
    "SendMessage(hClientWnd, WM_DDE_ACK, (WPARAM)hProxyWnd, lParam);",
    "msg.message == WM_DDE_EXECUTE",
    "msg.message == WM_DDE_REQUEST",
    "UnpackDDElParam(WM_DDE_REQUEST, lParam, &lo, &hi)",
    "Dde_SetRequestProxyWnd(hClientWnd, hi, hProxyWnd);",
    "WM_COPYDATA",
    "PostMessage(hClientWnd, WM_DDE_ACK, (WPARAM)hProxyWnd, msg.lParam);",
    "PostMessage(",
    "hClientWnd, WM_DDE_DATA, (WPARAM)hProxyWnd, msg.lParam",
]:
    require(proxy_block, term, "DdeProxyThreadSlave DDE topology")

for term in [
    "SREV-293: DDE proxy topology for restricted-token message delivery.",
    "private win32k behavior, not an API contract",
    "Gui_DDE_COPYDATA_Received",
    "Gui_DDE_Post_In_Box",
]:
    require(guidde, term, "guidde adjacency")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "GUI_DDE_SERVICE_PROXY_TOPOLOGY_COMMENT",
    "DdeProxyThreadSlave",
    "out-of-sandbox transport endpoint",
    "restricted-token posted-DDE topology",
    "`WM_COPYDATA` as a copy boundary",
    "SREV-084",
    "SREV-293",
    "SREV-347",
    "SREV-348",
    "Runtime gate:",
]:
    require(spec, term, "spec")

for text, label, terms in [
    (srev_084, "SREV-084 adjacency", ["DDE_PROXY_ACK_LPARAM_FORWARDING", "forwards the received ACK `lParam` unchanged", "DdeProxyThreadSlave"]),
    (srev_293, "SREV-293 adjacency", ["GUIDDE_DDE_PROXY_TOPOLOGY_COMMENT", "restricted-token", "private win32k path as observed behavior"]),
    (srev_347, "SREV-347 adjacency", ["GUI_DDE_ACK_PROXY_WINDOW_VALIDATION", "direct `SendMessageA/W`", "IsWindow"]),
    (srev_348, "SREV-348 adjacency", ["GUI_DDE_DATA_PROXY_ROUTE_MAP", "Dde_SetRequestProxyWnd", "Dde_TakeRequestProxyWnd"]),
]:
    for term in terms:
        require(text, term, label)

for term in [
    "### SREV-351: GUI DDE Service Proxy Topology Comment",
    "GUI_DDE_SERVICE_PROXY_TOPOLOGY_COMMENT",
    "srev-351-gui-dde-service-proxy-topology-comment.schema.json",
    "Sandboxie/core/svc/GuiServer.cpp",
    "DdeProxyThreadSlave",
    "WM_COPYDATA",
    "SREV-084",
    "SREV-293",
    "SREV-347",
    "SREV-348",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-351 source gate passed")
