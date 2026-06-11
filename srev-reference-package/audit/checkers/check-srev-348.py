#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-348 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-348 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-348-gui-dde-data-proxy-route-map.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-348 failed: schema is not draft-07")
if schema.get("id") != "GUI_DDE_DATA_PROXY_ROUTE_MAP":
    raise SystemExit("SREV-348 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/svc/GuiServer.cpp":
    raise SystemExit("SREV-348 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "pending request identity rather than by one process-global proxy HWND",
    "real client HWND plus the DDE item atom",
    "WM_DDE_REQUEST item atom with UnpackDDElParam",
    "Gui_DDE_DATA_Posting sends the real client HWND",
    "takes and removes the matching route",
    "Missing routes fail without posting",
    "Windows runtime proof is still required",
]:
    require(contracts, term, "schema")

svc = (ROOT / "Sandboxie/core/svc/GuiServer.cpp").read_text()
guidde = (ROOT / "Sandboxie/core/dll/guidde.c").read_text()
guimsg = (ROOT / "Sandboxie/core/dll/guimsg.c").read_text()
wire = (ROOT / "Sandboxie/core/svc/GuiWire.h").read_text()
spec = (ROOT / "docs/plan/srev-348-gui-dde-data-proxy-route-map.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-348.md").read_text()

for term in [
    "#define DDE_REQUEST_PROXY_WND_MAX 64",
    "typedef struct _DDE_REQUEST_PROXY_WND",
    "HWND client_hwnd;",
    "ULONG_PTR item_atom;",
    "HWND proxy_hwnd;",
    "static CRITICAL_SECTION DDE_Request_ProxyWndLock;",
    "static DDE_REQUEST_PROXY_WND DDE_Request_ProxyWnds[DDE_REQUEST_PROXY_WND_MAX];",
    "static void Dde_SetRequestProxyWnd(HWND client_hwnd, ULONG_PTR item_atom, HWND proxy_hwnd);",
    "static HWND Dde_TakeRequestProxyWnd(HWND client_hwnd, ULONG_PTR item_atom);",
    "InitializeCriticalSection(&DDE_Request_ProxyWndLock);",
    "DeleteCriticalSection(&DDE_Request_ProxyWndLock);",
]:
    require(svc, term, "route map declarations")

for term in [
    "static void Dde_SetRequestProxyWnd(HWND client_hwnd, ULONG_PTR item_atom, HWND proxy_hwnd)",
    "EnterCriticalSection(&DDE_Request_ProxyWndLock);",
    "entry->client_hwnd == client_hwnd && entry->item_atom == item_atom",
    "slot->client_hwnd = client_hwnd;",
    "slot->item_atom = item_atom;",
    "slot->proxy_hwnd = proxy_hwnd;",
    "slot->tick_count = GetTickCount();",
    "LeaveCriticalSection(&DDE_Request_ProxyWndLock);",
]:
    require(svc, term, "Dde_SetRequestProxyWnd")

for term in [
    "static HWND Dde_TakeRequestProxyWnd(HWND client_hwnd, ULONG_PTR item_atom)",
    "proxy_hwnd = entry->proxy_hwnd;",
    "memzero(entry, sizeof(DDE_REQUEST_PROXY_WND));",
    "return proxy_hwnd;",
]:
    require(svc, term, "Dde_TakeRequestProxyWnd")

send_copydata_start = svc.index("ULONG GuiServer::SendCopyDataSlave(")
send_copydata_end = svc.index("//---------------------------------------------------------------------------\n// ShellNotifyIconSlave", send_copydata_start)
send_copydata = svc[send_copydata_start:send_copydata_end]

for term in [
    "else if (req->which == 'dde ')",
    "SREV-348 routes this through the pending",
    "Dde_TakeRequestProxyWnd(hwnd, (ULONG_PTR)req->cds_key);",
    "if (hProxyWnd)",
    "PackDDElParam(WM_DDE_DATA",
    "(UINT_PTR)hGlobal, (UINT_PTR)req->cds_key",
    "PostMessage(",
    "hProxyWnd, (WM_USER + 0x123), tzuk, lparam",
    "args->rpl_len = sizeof(GUI_SEND_COPYDATA_RPL);",
    "return STATUS_SUCCESS;",
]:
    require(send_copydata, term, "SendCopyDataSlave DDE DATA route")

proxy_start = svc.index("ULONG GuiServer::DdeProxyThreadSlave(")
proxy_end = svc.index("//---------------------------------------------------------------------------\n// KillJob", proxy_start)
proxy_block = svc[proxy_start:proxy_end]

for term in [
    "msg.message == WM_DDE_REQUEST",
    "UnpackDDElParam(WM_DDE_REQUEST, lParam, &lo, &hi)",
    "Dde_SetRequestProxyWnd(hClientWnd, hi, hProxyWnd);",
    "msg.message == (WM_USER + 0x123) && msg.wParam == tzuk",
    "PostMessage(",
    "hClientWnd, WM_DDE_DATA, (WPARAM)hProxyWnd, msg.lParam",
]:
    require(proxy_block, term, "DdeProxyThreadSlave DDE request/data route")

for term in [
    "static HWND DDE_Request_ProxyWnd = NULL;",
    "global variable hack",
    "DDE_Request_ProxyWnd =",
    "PostMessage(DDE_Request_ProxyWnd",
    "wparam = (WPARAM)DDE_Request_ProxyWnd;",
]:
    reject(svc, term, "single global DDE proxy route")

data_post_start = guidde.index("_FX LRESULT Gui_DDE_DATA_Posting(")
data_post = guidde[data_post_start:]
for term in [
    "__sys_UnpackDDElParam(WM_DDE_DATA, lParam, &lo, &hi)",
    "req->msgid = GUI_SEND_COPYDATA;",
    "req->which = 'dde ';",
    "req->hwnd = (ULONG)(ULONG_PTR)TlsData->gui_dde_client_hwnd;",
    "req->cds_key = (ULONG64)(ULONG_PTR)hi;",
    "req->cds_len = DdeDataLen;",
]:
    require(data_post, term, "Gui_DDE_DATA_Posting route payload")

for term in [
    "if (Gui_UseProxyService && uMsg == WM_DDE_DATA)",
    "lResult = Gui_DDE_DATA_Posting(hWnd, wParam, lParam);",
]:
    require(guimsg, term, "Gui_PostMessage DDE DATA hook")

for term in [
    "struct tagGUI_SEND_COPYDATA_REQ",
    "ULONG which;",
    "ULONG hwnd;",
    "ULONG64 cds_key;",
    "ULONG cds_len;",
    "UCHAR cds_buf[1];",
]:
    require(wire, term, "GuiWire copydata ABI")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "DDE server responds to",
    "`WM_DDE_DATA` carries a",
    "atom identifying the data item",
    "`PostMessage` as posting to the queue",
    "Runtime gate:",
]:
    require(spec, term, "spec")

for term in [
    "### SREV-348: GUI DDE DATA Proxy Route Map",
    "GUI_DDE_DATA_PROXY_ROUTE_MAP",
    "srev-348-gui-dde-data-proxy-route-map.schema.json",
    "Sandboxie/core/svc/GuiServer.cpp",
    "Dde_SetRequestProxyWnd",
    "Dde_TakeRequestProxyWnd",
    "WM_DDE_DATA",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-348 source gate passed")
