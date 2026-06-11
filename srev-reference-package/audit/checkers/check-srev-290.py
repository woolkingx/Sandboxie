#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-290 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-290 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-290-gui-chrome-message-only-window-inactive-path.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-290 failed: schema is not draft-07")
if schema.get("id") != "GUI_CHROME_MESSAGE_ONLY_WINDOW_INACTIVE_PATH":
    raise SystemExit("SREV-290 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/dll/gui.c":
    raise SystemExit("SREV-290 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "Gui_CreateWindowExW owns active title class parent and CreateWindowExW forwarding policy",
    "the Dll_ChromeSandbox WS_CHILD HWND_MESSAGE branch remains inactive",
    "HWND_MESSAGE creates message-only windows that do not receive broadcast messages",
    "DDE initiation may broadcast WM_DDE_INITIATE to top-level windows",
    "branch revival requires Windows runtime proof and must not be driven by stale symptom wording",
    "SREV-084 owns active DDE proxy ACK payload forwarding",
    "this SREV changes comments and proof only",
]:
    require(contracts, term, "schema")

source = (ROOT / "Sandboxie/core/dll/gui.c").read_text()
spec = (ROOT / "docs/plan/srev-290-gui-chrome-message-only-window-inactive-path.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-290.md").read_text()
srev_084 = (ROOT / "docs/plan/ledger/srev-084.md").read_text()

func_start = source.index("_FX HWND Gui_CreateWindowExW(")
func_end = source.index("//---------------------------------------------------------------------------\n// Gui_CreateWindowExA", func_start)
func = source[func_start:func_end]

for term in [
    "SREV-290: inactive legacy Chrome message-only window experiment.",
    "HWND_MESSAGE creates a message-only window that does not receive",
    "broadcast messages, while DDE initiation may broadcast to top-level",
    "Keep this branch inactive until Windows runtime proof shows",
    "Chrome child top-level windows should cross into message-only topology.",
    "/*if (Dll_ChromeSandbox) { \n        dwStyle |= WS_CHILD;\n        hWndParent = HWND_MESSAGE;\n    }*/",
    "new_WindowName = Gui_CreateTitleW((WCHAR *)lpWindowName);",
    "clsnm = Gui_CreateClassNameW(lpClassName);",
    "if (hWndParent && (hWndParent != HWND_MESSAGE)\n                            && (! __sys_IsWindow(hWndParent)))",
    "hwndResult = __sys_CreateWindowExW(",
]:
    require(func, term, "Gui_CreateWindowExW source")

for stale in [
    "hang for several seconds",
    "To workaround this",
    "breaks Chrome hw acceleration",
    "reason not known",
]:
    reject(func, stale, "legacy Chrome message-only comment")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "GUI_CHROME_MESSAGE_ONLY_WINDOW_INACTIVE_PATH",
    "CreateWindowExW",
    "HWND_MESSAGE",
    "message-only",
    "WM_DDE_INITIATE",
    "SREV-084",
    "`Dll_ChromeSandbox` predicate",
    "`WS_CHILD` mutation",
    "`HWND_MESSAGE` assignment",
]:
    require(spec, term, "spec")

for term in [
    "DDE_PROXY_ACK_LPARAM_FORWARDING",
    "WM_DDE_ACK",
    "WM_DDE_EXECUTE",
    "WM_DDE_REQUEST",
    "DDE proxy",
]:
    require(srev_084, term, "SREV-084 adjacency")

for term in [
    "### SREV-290: GUI Chrome Message-Only Window Inactive Path",
    "GUI_CHROME_MESSAGE_ONLY_WINDOW_INACTIVE_PATH",
    "srev-290-gui-chrome-message-only-window-inactive-path.schema.json",
    "Sandboxie/core/dll/gui.c",
    "Gui_CreateWindowExW",
    "HWND_MESSAGE",
    "SREV-084",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-290 source gate passed")
