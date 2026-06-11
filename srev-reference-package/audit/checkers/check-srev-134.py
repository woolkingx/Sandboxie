#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-134 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-134 failed: {label} still contains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-134-driverassist-clipboard-probe-hglobal-ownership.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-134 failed: schema is not draft-07")
if schema.get("id") != "DRIVERASSIST_CLIPBOARD_PROBE_HGLOBAL_OWNERSHIP":
    raise SystemExit("SREV-134 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "InitClipboard creates four unique movable memory objects for the four driver-probe clipboard formats",
    "GlobalAlloc failure prevents clipboard probing and still releases every allocated local object",
    "GlobalLock failure prevents clipboard probing and still releases every allocated local object",
    "InitClipboard dereferences a GlobalLock pointer only after the pointer is non-null",
    "SetClipboardData receives one unique HGLOBAL per private probe format",
    "Gui_InitClipboard still observes the same four format markers in the same order",
]:
    require(contracts, term, "schema")

source = (ROOT / "Sandboxie/core/svc/DriverAssistStart.cpp").read_text()
driver_gui = (ROOT / "Sandboxie/core/drv/gui.c").read_text()
spec = (ROOT / "docs/plan/srev-134-driverassist-clipboard-probe-hglobal-ownership.md").read_text()
ledger = read_combined_ledger(ROOT)

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

init_clipboard = source[
    source.index("void DriverAssist::InitClipboard()"):
]
for term in [
    "const UINT Formats[4] = { 0x111111, 0x222222, 0x333333, 0x444444 };",
    "HGLOBAL hGlobal[4] = { NULL, NULL, NULL, NULL };",
    "bool globals_ok = true;",
    "for (int index = 0; index < 4; ++index) {",
    "hGlobal[index] = GlobalAlloc(GMEM_MOVEABLE, 8 * sizeof(WCHAR));",
    "if (! hGlobal[index]) {",
    "globals_ok = false;",
    "WCHAR *pGlobal = (WCHAR *)GlobalLock(hGlobal[index]);",
    "if (! pGlobal) {",
    "*pGlobal = L'\\0';",
    "GlobalUnlock(hGlobal[index]);",
    "if (globals_ok) {",
    "if (OpenClipboard(NULL)) {",
    "EmptyClipboard();",
    "SetClipboardData(Formats[index], hGlobal[index]);",
    "SbieApi_Call(API_GUI_CLIPBOARD, 1, (ULONG_PTR)-1);",
    "EmptyClipboard();",
    "CloseClipboard();",
    "GlobalFree(hGlobal[index]);",
]:
    require(init_clipboard, term, "InitClipboard")

for stale in [
    "HANDLE hGlobal1 = GlobalAlloc",
    "HANDLE hGlobal2 = GlobalAlloc",
    "SetClipboardData(0x111111, hGlobal1);",
    "SetClipboardData(0x222222, hGlobal1);",
    "SetClipboardData(0x333333, hGlobal2);",
    "SetClipboardData(0x444444, hGlobal2);",
]:
    reject(init_clipboard, stale, "stale shared HGLOBAL clipboard probe")

if init_clipboard.index("if (! pGlobal)") > init_clipboard.index("*pGlobal = L'\\0';"):
    raise SystemExit("SREV-134 failed: GlobalLock pointer is used before NULL gate")
if init_clipboard.index("SbieApi_Call(API_GUI_CLIPBOARD") < init_clipboard.index("SetClipboardData(Formats[index], hGlobal[index]);"):
    raise SystemExit("SREV-134 failed: driver probe runs before clipboard formats are placed")
if init_clipboard.index("GlobalFree(hGlobal[index]);") < init_clipboard.index("CloseClipboard();"):
    raise SystemExit("SREV-134 failed: local HGLOBAL free moved before clipboard cleanup")

gui_init = driver_gui[
    driver_gui.index("_FX void Gui_InitClipboard(void)"):
    driver_gui.index("//---------------------------------------------------------------------------\n// Gui_FixClipboard")
]
for term in [
    "placed four unique items",
    "if (Clipboard->count < 4)",
    "if (*ptr != 0x111111)",
    "if (*ptr != 0x222222)",
    "if (*ptr != 0x333333)",
    "if (*ptr != 0x444444)",
    "Gui_ClipboardItemLength = x2;",
    "Gui_ClipboardIntegrityIndex = i;",
]:
    require(gui_init, term, "Gui_InitClipboard")

for term in [
    "### SREV-134: DriverAssist Clipboard Probe HGLOBAL Ownership",
    "DRIVERASSIST_CLIPBOARD_PROBE_HGLOBAL_OWNERSHIP",
    "srev-134-driverassist-clipboard-probe-hglobal-ownership.schema.json",
    "Sandboxie/core/svc/DriverAssistStart.cpp",
    "Sandboxie/core/drv/gui.c",
    "DriverAssist::InitClipboard",
    "Gui_InitClipboard",
    "GlobalAlloc",
    "GlobalLock",
    "SetClipboardData",
    "EmptyClipboard",
    "API_GUI_CLIPBOARD",
]:
    require(ledger, term, "ledger")

print("SREV-134 schema/source gate passed")
