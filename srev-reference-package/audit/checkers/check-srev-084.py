#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-084 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-084 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-084-dde-proxy-ack-lparam.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-084 failed: schema is not draft-07")
if schema.get("id") != "DDE_PROXY_ACK_LPARAM_FORWARDING":
    raise SystemExit("SREV-084 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "transport boundary",
    "received server WM_DDE_ACK",
    "forwards the received ACK lParam unchanged",
    "must not reuse the previous client EXECUTE/REQUEST lParam",
    "WM_COPYDATA bridge payloads are copied",
]:
    require(contracts, term, "schema")

guidde = (ROOT / "Sandboxie/core/dll/guidde.c").read_text()
svc = (ROOT / "Sandboxie/core/svc/GuiServer.cpp").read_text()
spec = (ROOT / "docs/plan/srev-084-dde-proxy-ack-lparam.md").read_text()
ledger = read_combined_ledger(ROOT)

for term in [
    "SREV-293: DDE proxy topology for restricted-token message delivery.",
    "This block records observed private win32k behavior, not an API contract:",
    "the compatibility topology uses one dummy proxy window in the sandbox and",
    "a second proxy window in the SbieSvc GUI Proxy process.",
    "Gui_DDE_COPYDATA_Received",
    "__sys_PackDDElParam(",
    "__sys_UnpackDDElParam(",
]:
    require(guidde, term, "guidde.c")

for term in [
    "There seems to be a bug in kernel win32k",
    "the workaround includes one dummy proxy window",
]:
    reject(guidde, term, "guidde.c topology wording")

for term in [
    "DdeProxyThreadSlave",
    "msg.message == WM_DDE_ACK && (HWND)msg.wParam == hServerWnd",
    "PostMessage(hClientWnd, WM_DDE_ACK, (WPARAM)hProxyWnd, msg.lParam);",
]:
    require(svc, term, "GuiServer.cpp")

ack_start = svc.index("if (msg.message == WM_DDE_ACK && (HWND)msg.wParam == hServerWnd)")
ack_end = svc.index("}", ack_start)
ack_block = svc[ack_start:ack_end]
if "PostMessage(hClientWnd, WM_DDE_ACK, (WPARAM)hProxyWnd, lParam);" in ack_block:
    raise SystemExit("SREV-084 failed: stale local lParam forwarding remains")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "### SREV-084: DDE Proxy ACK lParam Forwarding",
    "DDE_PROXY_ACK_LPARAM_FORWARDING",
    "srev-084-dde-proxy-ack-lparam.schema.json",
]:
    require(ledger, term, "ledger")

print("SREV-084 schema/source gate passed")
