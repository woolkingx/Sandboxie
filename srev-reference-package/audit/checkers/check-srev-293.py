#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-293 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-293 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-293-guidde-dde-proxy-topology-comment.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-293 failed: schema is not draft-07")
if schema.get("id") != "GUIDDE_DDE_PROXY_TOPOLOGY_COMMENT":
    raise SystemExit("SREV-293 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/dll/guidde.c":
    raise SystemExit("SREV-293 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "guidde.c owns local DDE hook and proxy translation logic",
    "SbieSvc GUI Proxy owns the out-of-process DDE proxy window and transport edge",
    "private win32k call-stack names are observation evidence not API contract",
    "the legal protocol shape remains documented DDE messages and payload helpers",
    "SREV-084 owns DDE ACK lParam forwarding behavior",
    "this SREV changes comments and proof only",
]:
    require(contracts, term, "schema")

guidde = (ROOT / "Sandboxie/core/dll/guidde.c").read_text()
guiserver = (ROOT / "Sandboxie/core/svc/GuiServer.cpp").read_text()
spec = (ROOT / "docs/plan/srev-293-guidde-dde-proxy-topology-comment.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-293.md").read_text()
srev_084 = (ROOT / "docs/plan/ledger/srev-084.md").read_text()

comment_start = guidde.index("// SUPPORT FOR DDE CONVERSATIONS")
comment_end = guidde.index("// Functions", comment_start)
comment = guidde[comment_start:comment_end]

for term in [
    "SREV-293: DDE proxy topology for restricted-token message delivery.",
    "This block records observed private win32k behavior, not an API contract:",
    "with restricted-token DDE conversations, GetMessage/PeekMessage by the",
    "xxxDDETrackGetMessageHook",
    "HMValidateHandleNoRipNoIL",
    "ValidateHandleSecure",
    "the compatibility topology uses one dummy proxy window in the sandbox and",
    "a second proxy window in the SbieSvc GUI Proxy process.",
    "Gui_DDE_INITIATE_Received",
    "Gui_DDE_ACK_Sending",
    "Gui_DDE_COPYDATA_Received",
]:
    require(comment, term, "guidde topology comment")

for stale in [
    "There seems to be a bug in kernel win32k",
    "the workaround includes one dummy proxy window",
]:
    reject(comment, stale, "guidde topology comment")

for term in [
    "_FX WPARAM Gui_DDE_INITIATE_Received",
    "TlsData->gui_dde_client_hwnd",
    "TlsData->gui_dde_proxy_hwnd",
    "_FX HWND Gui_DDE_ACK_Sending",
    "_FX BOOLEAN Gui_DDE_COPYDATA_Received",
    "_FX BOOLEAN Gui_DDE_Post_In_Box",
    "__sys_PackDDElParam",
    "__sys_UnpackDDElParam",
]:
    require(guidde, term, "guidde DDE flow")

for term in [
    "DdeProxyThreadSlave",
    "SendPostMessageSlave",
    "AllowSendPostMessage",
]:
    require(guiserver, term, "SbieSvc DDE proxy adjacency")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "GUIDDE_DDE_PROXY_TOPOLOGY_COMMENT",
    "private win32k path as observed behavior",
    "documented DDE message protocol",
    "DDE payload shape",
    "SREV-084",
    "WM_DDE_INITIATE",
    "WM_DDE_EXECUTE",
    "WM_DDE_ACK",
    "WM_COPYDATA",
]:
    require(spec, term, "spec")

for term in [
    "DDE_PROXY_ACK_LPARAM_FORWARDING",
    "received server `WM_DDE_ACK`",
    "forwards the received ACK `lParam` unchanged",
    "DdeProxyThreadSlave",
]:
    require(srev_084, term, "SREV-084 adjacency")

for term in [
    "### SREV-293: GuiDDE DDE Proxy Topology Comment",
    "GUIDDE_DDE_PROXY_TOPOLOGY_COMMENT",
    "srev-293-guidde-dde-proxy-topology-comment.schema.json",
    "Sandboxie/core/dll/guidde.c",
    "SREV-084",
    "DdeProxyThreadSlave",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-293 source gate passed")
