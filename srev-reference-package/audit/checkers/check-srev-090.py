#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-090 failed: {label} missing {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-090-guititle-realgetwindowclass-buffer-shape.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-090 failed: schema is not draft-07")
if schema.get("id") != "GUITITLE_REALGETWINDOWCLASS_BUFFER_SHAPE":
    raise SystemExit("SREV-090 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "WCHAR character count, not a byte count",
    "ARRAYSIZE(clsnm)",
    "NUL-terminated before wcsstr / _wcsicmp",
    "Office caption-class skip",
    "Edit controls remain excluded",
    "GetWindowText / SendMessage / WM_SETTEXT",
]:
    require(contracts, term, "schema")

src = (ROOT / "Sandboxie/core/dll/guititle.c").read_text()
gui = (ROOT / "Sandboxie/core/dll/gui.c").read_text()
guimsg = (ROOT / "Sandboxie/core/dll/guimsg.c").read_text()
guienum = (ROOT / "Sandboxie/core/dll/guienum.c").read_text()
guicon = (ROOT / "Sandboxie/core/dll/guicon.c").read_text()
spec = (ROOT / "docs/plan/srev-090-guititle-realgetwindowclass-buffer-shape.md").read_text()
ledger = read_combined_ledger(ROOT)

for term in [
    "WCHAR clsnm[256];",
    "__sys_RealGetWindowClassW(hWnd, clsnm, ARRAYSIZE(clsnm));",
    "if (nChars >= ARRAYSIZE(clsnm))",
    "nChars = ARRAYSIZE(clsnm) - 1;",
    "clsnm[nChars] = L'\\0';",
]:
    require(src, term, "guititle.c class buffer shape")

for stale in [
    "__sys_RealGetWindowClassW(hWnd, clsnm, sizeof(clsnm) - 1)",
    "$Workaround$ - 3rd party fix",
]:
    if stale in src:
        raise SystemExit(f"SREV-090 failed: stale guititle shape remains {stale!r}")

class_index = src.index("__sys_RealGetWindowClassW(hWnd, clsnm, ARRAYSIZE(clsnm));")
nul_index = src.index("clsnm[nChars] = L'\\0';", class_index)
office_index = src.index("wcsstr(clsnm, L\":XLMAIN\")")
edit_index = src.index("_wcsicmp(clsnm, L\"Edit\")")
if not (class_index < nul_index < office_index < edit_index):
    raise SystemExit("SREV-090 failed: class string must be terminated before consumers")

for term in [
    "if ((style & WS_CAPTION) == WS_CAPTION)",
    "__sys_GetWindowRect(hWnd, &windowRect)",
    "__sys_ClientToScreen(hWnd, &clientOrigin)",
    "if (titleBarHeight < 10)",
    "wcsstr(clsnm, L\":XLMAIN\")",
    "wcsstr(clsnm, L\":OpusApp\")",
    "wcsstr(clsnm, L\":PPTFrameClass\")",
    "wcsstr(clsnm, L\":MSWinPub\")",
    "wcsstr(clsnm, L\":rctrl_renwnd32\")",
    "wcsstr(clsnm, L\":Framework::CFrame\")",
    "_wcsicmp(clsnm, L\"Edit\") != 0",
]:
    require(src, term, "guititle.c title/class gate preservation")

for term in [
    "Gui_GetWindowTextW(",
    "Gui_GetWindowTextA(",
    "Gui_ShouldCreateTitle(hWnd)",
    "Gui_CreateTitleW(",
    "Gui_CreateTitleA(",
    "Gui_FixTitleW(",
    "Gui_FixTitleA(",
]:
    require(src, term, "guititle.c title helper owner")

for text, label, terms in [
    (
        gui,
        "gui.c title mutation consumer",
        [
            "Gui_CreateTitleW((WCHAR *)lpWindowName)",
            "Gui_CreateTitleA((UCHAR *)lpWindowName)",
            "if (uMsg == WM_SETTEXT && Gui_ShouldCreateTitle(hWnd))",
        ],
    ),
    (
        guimsg,
        "guimsg.c title query consumer",
        [
            "Gui_FixTitleA(hWnd, (UCHAR *)lParam, (int)lResult)",
            "Gui_FixTitleW(hWnd, (WCHAR *)lParam, (int)lResult)",
        ],
    ),
    (
        guienum,
        "guienum.c title enumeration consumer",
        [
            "Gui_CreateTitleW(lpWindowName)",
            "Gui_CreateTitleA(lpWindowName)",
        ],
    ),
    (
        guicon,
        "guicon.c console title consumer",
        [
            "Gui_CreateTitleW(lpConsoleTitle)",
            "Gui_CreateTitleA(lpConsoleTitle)",
            "Gui_FixTitleW((HWND)(ULONG_PTR)tzuk",
            "Gui_FixTitleA((HWND)(ULONG_PTR)tzuk",
        ],
    ),
]:
    for term in terms:
        require(text, term, label)

for term in [
    "WM_SETTEXT",
]:
    require(gui, term, "gui.c title rewrite topology")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "### SREV-090: GUI Title RealGetWindowClass Buffer Shape",
    "GUITITLE_REALGETWINDOWCLASS_BUFFER_SHAPE",
    "srev-090-guititle-realgetwindowclass-buffer-shape.schema.json",
]:
    require(ledger, term, "ledger")

print("SREV-090 schema/source gate passed")
