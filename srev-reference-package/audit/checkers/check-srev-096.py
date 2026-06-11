#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-096 failed: {label} missing {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-096-clipboard-window-station-reference-owner.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-096 failed: schema is not draft-07")
if schema.get("id") != "CLIPBOARD_WINDOW_STATION_REFERENCE_OWNER":
    raise SystemExit("SREV-096 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "only from SbieSvc",
    "window-station handle is only a handle source",
    "hold the window-station object while clipboard memory is read or modified",
    "clipboard pointer is valid only inside the held window-station reference scope",
    "Gui_InitClipboard must release the reference on every exit",
    "Gui_FixClipboard must release the reference after mutating",
    "private clipboard layout discovery remains Dyndata/version gated",
    "SbieSvc remains the clipboard open/lock and delayed-rendering owner",
]:
    require(contracts, term, "schema")

gui_drv = (ROOT / "Sandboxie/core/drv/gui.c").read_text()
guimisc = (ROOT / "Sandboxie/core/dll/guimisc.c").read_text()
gui_server = (ROOT / "Sandboxie/core/svc/GuiServer.cpp").read_text()
assist = (ROOT / "Sandboxie/core/svc/DriverAssistStart.cpp").read_text()
spec = (ROOT / "docs/plan/srev-096-clipboard-window-station-reference-owner.md").read_text()
ledger = read_combined_ledger(ROOT)

for term in [
    "typedef struct _GUI_CLIPBOARD_REF",
    "GUI_CLIPBOARD *clipboard;",
    "void *window_station;",
    "static BOOLEAN Gui_ReferenceClipboard(GUI_CLIPBOARD_REF *ref);",
    "static void Gui_DereferenceClipboard(GUI_CLIPBOARD_REF *ref);",
    "_FX BOOLEAN Gui_ReferenceClipboard(GUI_CLIPBOARD_REF *ref)",
    "memzero(ref, sizeof(GUI_CLIPBOARD_REF));",
    "PsGetProcessWin32WindowStation(PsGetCurrentProcess())",
    "ObReferenceObjectByHandle(",
    "*ExWindowStationObjectType, KernelMode",
    "ref->clipboard = Clipboard;",
    "ref->window_station = WinStaObject;",
    "_FX void Gui_DereferenceClipboard(GUI_CLIPBOARD_REF *ref)",
    "ObDereferenceObject(ref->window_station);",
]:
    require(gui_drv, term, "gui.c reference owner")

stale = "ObDereferenceObject(WinStaObject);\n\n    //\n    // get the clipboard data in the window station object"
if stale in gui_drv:
    raise SystemExit("SREV-096 failed: stale immediate dereference before clipboard pointer remains")
if "static GUI_CLIPBOARD *Gui_GetClipboard(void);" in gui_drv:
    raise SystemExit("SREV-096 failed: stale Gui_GetClipboard prototype remains")
if "_FX GUI_CLIPBOARD *Gui_GetClipboard(void)" in gui_drv:
    raise SystemExit("SREV-096 failed: stale Gui_GetClipboard implementation remains")

init_start = gui_drv.index("_FX void Gui_InitClipboard(void)")
fix_start = gui_drv.index("_FX void Gui_FixClipboard(ULONG integrity)")
api_start = gui_drv.index("_FX NTSTATUS Gui_Api_Clipboard")
init_body = gui_drv[init_start:fix_start]
fix_body = gui_drv[fix_start:api_start]

for term in [
    "GUI_CLIPBOARD_REF ClipboardRef;",
    "if (! Gui_ReferenceClipboard(&ClipboardRef))",
    "Clipboard = ClipboardRef.clipboard;",
    "goto finish;",
    "Gui_DereferenceClipboard(&ClipboardRef);",
]:
    require(init_body, term, "Gui_InitClipboard reference lifetime")

post_acquire = init_body[init_body.index("Clipboard = ClipboardRef.clipboard;"):]
finish_index = post_acquire.index("finish:")
if "return;" in post_acquire[:finish_index]:
    raise SystemExit("SREV-096 failed: Gui_InitClipboard has a post-acquisition return before finish")

for term in [
    "GUI_CLIPBOARD_REF ClipboardRef;",
    "if (! Gui_ReferenceClipboard(&ClipboardRef))",
    "Clipboard = ClipboardRef.clipboard;",
    "for (i = 0; i < Clipboard->count; ++i)",
    "ptr[Gui_ClipboardIntegrityIndex] = integrity;",
    "Gui_DereferenceClipboard(&ClipboardRef);",
]:
    require(fix_body, term, "Gui_FixClipboard reference lifetime")

if fix_body.index("Gui_DereferenceClipboard(&ClipboardRef);") < fix_body.index("for (i = 0; i < Clipboard->count; ++i)"):
    raise SystemExit("SREV-096 failed: Gui_FixClipboard releases the reference before mutation loop")

for term in [
    "Dyndata_Config.Clipboard_offset",
    "0x111111",
    "0x222222",
    "0x333333",
    "0x444444",
    "0x4000",
    "Gui_ClipboardItemLength",
    "Gui_ClipboardIntegrityIndex",
    "if (proc || (! MyIsCallerMyServiceProcess()))",
    "STATUS_ACCESS_DENIED",
]:
    require(gui_drv, term, "gui.c clipboard policy preservation")

for term in [
    "BOOL ok = __sys_CloseClipboard();",
    "Gui_CallProxyEx(",
    "GUI_CLOSE_CLIPBOARD",
    "Delay rendered",
]:
    require(guimisc, term, "guimisc.c proxy path")

for term in [
    "OpenClipboard(NULL)",
    "SbieApi_Call(API_GUI_CLIPBOARD, 1, (ULONG_PTR)0x4000)",
    "EnumClipboardFormats(fmt)",
    "GetClipboardData(fmt)",
    "CloseClipboard();",
]:
    require(gui_server, term, "GuiServer delayed rendering owner")

for term in [
    "const UINT Formats[4] = { 0x111111, 0x222222, 0x333333, 0x444444 };",
    "HGLOBAL hGlobal[4] = { NULL, NULL, NULL, NULL };",
    "SetClipboardData(Formats[index], hGlobal[index]);",
    "SbieApi_Call(API_GUI_CLIPBOARD, 1, (ULONG_PTR)-1)",
]:
    require(assist, term, "DriverAssist layout discovery")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "window station as a securable object",
    "contains a clipboard",
    "object body and incrementing",
    "paired contract",
    "delayed rendering",
    "Mandatory Integrity Control",
]:
    require(spec, term, "spec official shape")

for term in [
    "### SREV-096: Clipboard Window-Station Reference Owner",
    "CLIPBOARD_WINDOW_STATION_REFERENCE_OWNER",
    "srev-096-clipboard-window-station-reference-owner.schema.json",
]:
    require(ledger, term, "ledger")

print("SREV-096 schema/source gate passed")
