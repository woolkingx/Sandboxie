#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-347 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-347 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-347-gui-dde-ack-proxy-window-validation.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-347 failed: schema is not draft-07")
if schema.get("id") != "GUI_DDE_ACK_PROXY_WINDOW_VALIDATION":
    raise SystemExit("SREV-347 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/svc/GuiServer.cpp":
    raise SystemExit("SREV-347 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "DDE conversation identity is a pair of participating window handles",
    "DDE ACK proxy startup is for direct SendMessageA and SendMessageW requests",
    "SendMessageTimeoutA and SendMessageTimeoutW remain on the normal timeout broker path",
    "validate the client HWND with IsWindow before allocating proxy arguments",
    "DdeProxyThreadSlave preserves the existing initial WM_DDE_ACK",
    "SREV-084 owns DDE ACK lParam forwarding",
    "Windows runtime proof is still required",
]:
    require(contracts, term, "schema")

svc = (ROOT / "Sandboxie/core/svc/GuiServer.cpp").read_text()
guimsg = (ROOT / "Sandboxie/core/dll/guimsg.c").read_text()
guidde = (ROOT / "Sandboxie/core/dll/guidde.c").read_text()
wire = (ROOT / "Sandboxie/core/svc/GuiWire.h").read_text()
spec = (ROOT / "docs/plan/srev-347-gui-dde-ack-proxy-window-validation.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-347.md").read_text()

send_start = svc.index("ULONG GuiServer::SendPostMessageSlave(")
send_end = svc.index("//---------------------------------------------------------------------------\n// SendCopyDataSlave", send_start)
send_block = svc[send_start:send_end]

dde_start = send_block.index("// WM_DDE_ACK")
dde_end = send_block.index("//\n    // check access according to OpenWinClass rules", dde_start)
dde_block = send_block[dde_start:dde_end]

proxy_start = svc.index("ULONG GuiServer::DdeProxyThreadSlave(")
proxy_end = svc.index("//---------------------------------------------------------------------------\n// KillJob", proxy_start)
proxy_block = svc[proxy_start:proxy_end]

send_a_start = guimsg.index("_FX LRESULT Gui_SendMessageA(")
send_a_end = guimsg.index("//---------------------------------------------------------------------------\n// Gui_SendMessageW", send_a_start)
send_a_block = guimsg[send_a_start:send_a_end]
send_w_start = guimsg.index("_FX LRESULT Gui_SendMessageW(")
send_w_end = guimsg.index("//---------------------------------------------------------------------------\n// Gui_SendMessageTimeoutA", send_w_start)
send_w_block = guimsg[send_w_start:send_w_end]
timeout_a_start = guimsg.index("_FX LRESULT Gui_SendMessageTimeoutA(")
timeout_w_end = guimsg.index("//---------------------------------------------------------------------------\n// Gui_PostMessageA", timeout_a_start)
timeout_block = guimsg[timeout_a_start:timeout_w_end]

for term in [
    "if (msg == WM_DDE_ACK &&",
    "(req->which == 'sm w' || req->which == 'sm a')",
    "SREV-347: when a sandboxed process sends WM_DDE_ACK through",
    "SendMessageA/W, it starts the DDE proxy conversation described",
    "Validate the client HWND before creating",
    "if (IsWindow(hwnd))",
    "HeapAlloc(GetProcessHeap(), 0, (sizeof(ULONG_PTR) * 4))",
    "DdeArgs[0] = (ULONG_PTR)hwnd;",
    "DdeArgs[1] = (ULONG_PTR)wparam;",
    "DdeArgs[2] = (ULONG_PTR)lparam;",
    "CreateThread(",
    "DdeProxyThreadSlave",
    "args->rpl_len = sizeof(GUI_SEND_POST_MESSAGE_RPL);",
]:
    require(dde_block, term, "SendPostMessageSlave DDE ACK proxy block")

for term in [
    "req->which == 'smtw'",
    "req->which == 'smta'",
    "if ((req->which == 'sm w') || (req->which == 'sm a')",
    "to work around the IL bug in DDE",
]:
    reject(dde_block, term, "DDE ACK proxy startup shape")

if dde_block.index("if (IsWindow(hwnd))") > dde_block.index("HeapAlloc(GetProcessHeap()"):
    raise SystemExit("SREV-347 failed: IsWindow occurs after DDE argument allocation")
if dde_block.index("if (IsWindow(hwnd))") > dde_block.index("CreateThread("):
    raise SystemExit("SREV-347 failed: IsWindow occurs after proxy thread creation")

for block, label, which in [
    (send_a_block, "Gui_SendMessageA", "'sm a'"),
    (send_w_block, "Gui_SendMessageW", "'sm w'"),
]:
    require(block, "if (uMsg == WM_DDE_ACK)", label)
    require(block, "hWnd = Gui_DDE_ACK_Sending(hWnd, wParam);", label)
    require(block, which, label)

for term in [
    "_FX LRESULT Gui_SendMessageTimeoutA(",
    "_FX LRESULT Gui_SendMessageTimeoutW(",
    "'smta'",
    "'smtw'",
]:
    require(timeout_block, term, "SendMessageTimeout routing")
reject(timeout_block, "Gui_DDE_ACK_Sending", "timeout DDE ACK mapping")

for term in [
    "THREAD_DATA *TlsData = Dll_GetTlsData(NULL);",
    "Gui_SetWindowProc((HWND)wParam, TRUE);",
    "if (hWnd == TlsData->gui_dde_proxy_hwnd)",
    "hWnd = TlsData->gui_dde_client_hwnd;",
]:
    require(guidde, term, "Gui_DDE_ACK_Sending topology")

for term in [
    "HWND hClientWnd = (HWND)DdeArgs[0];",
    "HWND hServerWnd = (HWND)DdeArgs[1];",
    "LPARAM lParam = (LPARAM)DdeArgs[2];",
    "SendMessage(hClientWnd, WM_DDE_ACK, (WPARAM)hProxyWnd, lParam);",
    "PostMessage(hClientWnd, WM_DDE_ACK, (WPARAM)hProxyWnd, msg.lParam);",
]:
    require(proxy_block, term, "DdeProxyThreadSlave topology")

for term in [
    "struct tagGUI_SEND_POST_MESSAGE_REQ",
    "ULONG which;",
    "ULONG hwnd;",
    "ULONG64 wparam;",
    "ULONG64 lparam;",
    "ULONG flags;",
    "ULONG timeout;",
]:
    require(wire, term, "GuiWire send/post ABI")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "DDE as a message protocol between client and server",
    "A DDE conversation is identified by the pair",
    "`WM_DDE_ACK` in response to",
    "`SendMessageTimeout` is a",
    "`IsWindow` checks whether a window",
    "Runtime gate:",
]:
    require(spec, term, "spec")

for term in [
    "### SREV-347: GUI DDE ACK Proxy Window Validation",
    "GUI_DDE_ACK_PROXY_WINDOW_VALIDATION",
    "srev-347-gui-dde-ack-proxy-window-validation.schema.json",
    "Sandboxie/core/svc/GuiServer.cpp",
    "SendPostMessageSlave",
    "DdeProxyThreadSlave",
    "IsWindow",
    "SendMessageTimeout",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-347 source gate passed")
