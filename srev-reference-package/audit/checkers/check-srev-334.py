#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-334 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-334 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-334-gui-clipboard-il-bridge.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-334 failed: schema is not draft-07")
if schema.get("id") != "GUI_CLIPBOARD_INTEGRITY_BRIDGE":
    raise SystemExit("SREV-334 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/drv/gui.c":
    raise SystemExit("SREV-334 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "public clipboard API owns open close ownership delayed rendering and format enumeration",
    "window station owns the documented clipboard container",
    "service-only because the driver does not own clipboard locking",
    "private runtime-probed clipboard item layout",
    "rewrites only known MIC integrity label slots",
    "win32k FindClipFormat names private observation evidence",
    "this SREV changes comments and proof only",
]:
    require(contracts, term, "schema")

drv = (ROOT / "Sandboxie/core/drv/gui.c").read_text()
svc = (ROOT / "Sandboxie/core/svc/GuiServer.cpp").read_text()
spec = (ROOT / "docs/plan/srev-334-gui-clipboard-il-bridge.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-334.md").read_text()

comment_start = drv.index("// SREV-334: Windows Vista+ clipboard access")
comment_end = drv.index("typedef struct _GUI_CLIPBOARD", comment_start)
comment = drv[comment_start:comment_end]

ref_start = drv.index("_FX BOOLEAN Gui_ReferenceClipboard(")
ref_end = drv.index("// Gui_DereferenceClipboard", ref_start)
ref_block = drv[ref_start:ref_end]

init_start = drv.index("_FX void Gui_InitClipboard(void)")
init_end = drv.index("// Gui_FixClipboard", init_start)
init_block = drv[init_start:init_end]

fix_start = drv.index("_FX void Gui_FixClipboard(ULONG integrity)")
fix_end = drv.index("// Gui_Api_Clipboard", fix_start)
fix_block = drv[fix_start:fix_end]

api_start = drv.index("_FX NTSTATUS Gui_Api_Clipboard(")
api_block = drv[api_start:]

close_start = svc.index("ULONG GuiServer::CloseClipboardSlave(")
close_end = svc.index("// GetClipboardDataSlave", close_start)
close_block = svc[close_start:close_end]

for term in [
    "SREV-334: Windows Vista+ clipboard access crosses the window-station",
    "clipboard, UIPI/MIC integrity labels, and Sandboxie's private clipboard",
    "item layout probe so out-of-sandbox readers can access sandbox copies.",
    "Private observation: win32k!FindClipFormat treats item IL = 0 poorly,",
    "To bridge this, API_GUI_CLIPBOARD adjusts",
    "CloseClipboardSlave",
    "Gui_CloseClipboard",
]:
    require(comment, term, "source comment")

for stale in [
    "Workaround for bug",
    "There seems to be a bug",
    "to work around this",
]:
    reject(comment, stale, "clipboard comment")

for term in [
    "PsGetProcessWin32WindowStation(PsGetCurrentProcess())",
    "ObReferenceObjectByHandle(",
    "*ExWindowStationObjectType",
    "Dyndata_Config.Clipboard_offset",
]:
    require(ref_block, term, "clipboard reference block")

for term in [
    "0x111111",
    "0x222222",
    "0x333333",
    "0x444444",
    "Gui_ClipboardItemLength = x2;",
    "Gui_ClipboardIntegrityIndex = i;",
    "Gui_ClipboardIntegrityIndex = -1;",
]:
    require(init_block, term, "clipboard init block")

for term in [
    "Gui_ClipboardIntegrityIndex != -1",
    "const ULONG il = ptr[Gui_ClipboardIntegrityIndex] & ~1;",
    "(il == 0x0000) || (il == 0x1000) || (il == 0x2000)",
    "ptr[Gui_ClipboardIntegrityIndex] = integrity;",
]:
    require(fix_block, term, "clipboard fix block")

for term in [
    "Driver_OsVersion < DRIVER_WINDOWS_VISTA",
    "if (proc || (! MyIsCallerMyServiceProcess()))",
    "(ULONG_PTR)parms[1] == -1",
    "Gui_InitClipboard();",
    "Gui_FixClipboard((ULONG)parms[1]);",
    "STATUS_UNKNOWN_REVISION",
]:
    require(api_block, term, "clipboard API block")

for term in [
    "OpenClipboard(NULL)",
    "SbieApi_Call(API_GUI_CLIPBOARD, 1, (ULONG_PTR)0x4000)",
    "EnumClipboardFormats(fmt)",
    "GetClipboardData(fmt)",
    "CloseClipboard();",
    "GetClipboardSequenceNumber()",
]:
    require(close_block, term, "CloseClipboardSlave block")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "### SREV-334: GUI Clipboard Integrity Bridge",
    "GUI_CLIPBOARD_INTEGRITY_BRIDGE",
    "srev-334-gui-clipboard-il-bridge.schema.json",
    "Sandboxie/core/drv/gui.c",
    "API_GUI_CLIPBOARD",
    "CloseClipboardSlave",
    "Dyndata_Config.Clipboard_offset",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-334 source gate passed")
