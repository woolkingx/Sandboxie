#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-294 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-294 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-294-guimisc-clipboard-proxy-topology-comment.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-294 failed: schema is not draft-07")
if schema.get("id") != "GUIMISC_CLIPBOARD_PROXY_TOPOLOGY_COMMENT":
    raise SystemExit("SREV-294 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/dll/guimisc.c":
    raise SystemExit("SREV-294 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "guimisc.c owns the user-mode CloseClipboard hook decision to call SbieSvc after a sequence change",
    "SbieSvc GUI Proxy owns delayed-rendering force and API_GUI_CLIPBOARD calls",
    "drv/gui.c owns private clipboard item layout discovery and integrity rewrite",
    "private win32k clipboard layout is observation evidence not API contract",
    "SREV-096 owns driver-side window-station reference and integrity rewrite gates",
    "SREV-134 owns service-side clipboard probe data shape",
    "clipboard viewer listener race remains a Windows runtime gate",
    "this SREV changes comments and proof only",
]:
    require(contracts, term, "schema")

guimisc = (ROOT / "Sandboxie/core/dll/guimisc.c").read_text()
guiserver = (ROOT / "Sandboxie/core/svc/GuiServer.cpp").read_text()
drvgui = (ROOT / "Sandboxie/core/drv/gui.c").read_text()
spec = (ROOT / "docs/plan/srev-294-guimisc-clipboard-proxy-topology-comment.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-294.md").read_text()
srev_096 = (ROOT / "docs/plan/ledger/srev-096.md").read_text()
srev_134 = (ROOT / "docs/plan/ledger/srev-134.md").read_text()

comment_start = guimisc.index("// Clipboard support functions")
comment_end = guimisc.index("// Gui_OpenClipboard", comment_start)
comment = guimisc[comment_start:comment_end]

for term in [
    "SREV-294: Clipboard close crosses into the SbieSvc proxy",
    "delayed",
    "rendering can be forced and private clipboard item integrity can be fixed.",
    "On UIPI systems each clipboard item carries integrity state;",
    "data copied by",
    "a sandboxed process can otherwise remain at integrity level zero and prevent",
    "an outside process from pasting.",
    "The private win32k clipboard layout is",
    "observation evidence, not an API contract; SREV-096 owns the driver-side",
    "window-station reference and integrity rewrite gate.",
    "The SbieSvc GUI Proxy owns the delayed-rendering and API_GUI_CLIPBOARD edge.",
]:
    require(comment, term, "guimisc clipboard comment")

for stale in [
    "process outside the sandbox copies",
    "perhaps a bug in win32k",
    "to work around both issues",
]:
    reject(comment, stale, "guimisc clipboard comment")

for term in [
    "_FX BOOL Gui_OpenClipboard(HWND hwnd)",
    "Gui_OpenClipboard_seq = __sys_GetClipboardSequenceNumber();",
    "_FX BOOL Gui_CloseClipboard(void)",
    "BOOL ok = __sys_CloseClipboard();",
    "ULONG new_seq = __sys_GetClipboardSequenceNumber();",
    "Gui_CallProxyEx(",
    "GUI_CLOSE_CLIPBOARD",
    "SetClipboardViewer or AddClipboardFormatListener",
]:
    require(guimisc, term, "guimisc close clipboard edge")

for term in [
    "GuiServer::CloseClipboardSlave",
    "OpenClipboard(NULL)",
    "EnumClipboardFormats",
    "GetClipboardData",
    "API_GUI_CLIPBOARD",
    "(ULONG_PTR)0x4000",
]:
    require(guiserver, term, "SbieSvc clipboard proxy adjacency")

for term in [
    "Gui_Api_Clipboard",
    "Gui_InitClipboard",
    "Gui_FixClipboard",
    "Gui_ReferenceClipboard",
    "Gui_DereferenceClipboard",
    "Dyndata_Config.Clipboard_offset",
]:
    require(drvgui, term, "driver clipboard adjacency")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "GUIMISC_CLIPBOARD_PROXY_TOPOLOGY_COMMENT",
    "Mandatory Integrity Control",
    "SetClipboardViewer",
    "AddClipboardFormatListener",
    "WM_CLIPBOARDUPDATE",
    "private win32k layout observation",
    "SREV-096",
    "SREV-134",
]:
    require(spec, term, "spec")

for term in [
    "CLIPBOARD_WINDOW_STATION_REFERENCE_OWNER",
    "API_GUI_CLIPBOARD",
    "ObReferenceObjectByHandle",
    "Gui_FixClipboard",
    "viewer/listener notification race",
]:
    require(srev_096, term, "SREV-096 adjacency")

for term in [
    "DRIVERASSIST_CLIPBOARD_PROBE_HGLOBAL_OWNERSHIP",
    "DriverAssist::InitClipboard",
    "four unique movable memory objects",
    "API_GUI_CLIPBOARD",
]:
    require(srev_134, term, "SREV-134 adjacency")

for term in [
    "### SREV-294: GuiMisc Clipboard Proxy Topology Comment",
    "GUIMISC_CLIPBOARD_PROXY_TOPOLOGY_COMMENT",
    "srev-294-guimisc-clipboard-proxy-topology-comment.schema.json",
    "Sandboxie/core/dll/guimisc.c",
    "Gui_CloseClipboard",
    "SREV-096",
    "SREV-134",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-294 source gate passed")
