#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-086 failed: {label} missing {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-086-guiclass-adobe-wm-create-class-shape.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-086 failed: schema is not draft-07")
if schema.get("id") != "GUI_ADOBE_WM_CREATE_CLASS_SHAPE":
    raise SystemExit("SREV-086 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "RegisterClassEx/CreateWindowEx class identity",
    "WM_NCCREATE and WM_CREATE pass CREATESTRUCT.lpszClass",
    "NoRename rather than relying on private callback offsets",
    "com.adobe.ape.stage and OWL.*",
    "GetClassName remains the public query boundary",
    "private KernelCallbackTable offsets are not extended",
]:
    require(contracts, term, "schema")

guiclass = (ROOT / "Sandboxie/core/dll/guiclass.c").read_text()
gui = (ROOT / "Sandboxie/core/dll/gui.c").read_text()
spec = (ROOT / "docs/plan/srev-086-guiclass-adobe-wm-create-class-shape.md").read_text()
ledger = read_combined_ledger(ROOT)

for term in [
    "wc.lpszClassName = Gui_CreateClassNameW(wc.lpszClassName);",
    "wc.lpszClassName = Gui_CreateClassNameA(wc.lpszClassName);",
    "clsnm = Gui_CreateClassNameW(lpClassName);",
    "clsnm = Gui_CreateClassNameA(lpClassName);",
    "if (Gui_NoRenameClass(iptr) || Gui_IsOpenClass(iptr))",
    "treat all well known classes as NoRenameWinClass",
]:
    require(guiclass, term, "guiclass.c class rename owner")

for term in [
    "L\"com.adobe.ape.stage\",",
    "if (ch == 'o' && _wcsnicmp(iptr, L\"OWL.\", 4) == 0)",
    "return TRUE;",
]:
    require(guiclass, term, "guiclass.c Adobe/OWL NoRename classification")

for stale in [
    "//L\"com.adobe.ape.stage\",     // FIXME",
    "// FIXME Adobe window classes having to do with the WM_CREATE problem",
    "//if (ch == 'o' && _wcsnicmp(iptr, L\"OWL.\", 4) == 0)",
]:
    if stale in guiclass:
        raise SystemExit(f"SREV-086 failed: stale commented classification remains: {stale!r}")

for term in [
    "KernelCallbackTable",
    "Gui_CREATESTRUCT_Handler",
    "index 10 is for __fnINLPCREATESTRUCT",
    "Gui_CREATESTRUCT_Restore",
]:
    require(guiclass, term, "guiclass.c private callback evidence")

for term in [
    "else if (uMsg == WM_CREATE || uMsg == WM_NCCREATE)",
    "Gui_CREATESTRUCT_Restore(lParam);",
]:
    require(gui, term, "gui.c DefWindowProc restore edge")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "### SREV-086: GUI Adobe WM_CREATE Class Shape",
    "GUI_ADOBE_WM_CREATE_CLASS_SHAPE",
    "srev-086-guiclass-adobe-wm-create-class-shape.schema.json",
]:
    require(ledger, term, "ledger")

print("SREV-086 schema/source gate passed")
