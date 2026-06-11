#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-292 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-292 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-292-guicon-console-taskbar-inactive-edge.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-292 failed: schema is not draft-07")
if schema.get("id") != "GUICON_CONSOLE_TASKBAR_INACTIVE_EDGE":
    raise SystemExit("SREV-292 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/dll/guicon.c":
    raise SystemExit("SREV-292 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "Gui_ConsoleThread owns helper-window message pumping and parent-thread wait behavior",
    "the Gui_ConsoleHwnd Taskbar_SetWindowAppUserModelId branch remains inactive",
    "taskbar.c owns Shell AppUserModelID and window property-store rewriting",
    "SREV-004 owns process AppUserModelID process-parameter workaround gates",
    "SREV-076 owns console helper thread handoff and cleanup",
    "SREV-241 owns taskbar caller topology",
    "branch revival requires Windows console git taskbar runtime proof",
    "this SREV changes comments and proof only",
]:
    require(contracts, term, "schema")

guicon = (ROOT / "Sandboxie/core/dll/guicon.c").read_text()
taskbar = (ROOT / "Sandboxie/core/dll/taskbar.c").read_text()
spec = (ROOT / "docs/plan/srev-292-guicon-console-taskbar-inactive-edge.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-292.md").read_text()
srev_004 = (ROOT / "docs/plan/ledger/srev-004.md").read_text()
srev_076 = (ROOT / "docs/plan/ledger/srev-076.md").read_text()
srev_241 = (ROOT / "docs/plan/ledger/srev-241.md").read_text()

start = guicon.index("_FX ULONG Gui_ConsoleThread(void *xHandles)")
end = guicon.index("while (__sys_PeekMessageW(&msg, NULL, 0, 0, PM_NOREMOVE))", start)
branch = guicon[start:end]

for term in [
    "SREV-292: inactive console AppUserModelID experiment.",
    "Console helper message pumping stays separate from taskbar",
    "window-property rewriting; reviving this edge requires Windows",
    "console/git runtime proof plus SREV-004/SREV-241 taskbar gates.",
    "while (1) {",
    "//if (Gui_ConsoleHwnd && Dll_InitComplete) {",
    "//    Taskbar_SetWindowAppUserModelId(Gui_ConsoleHwnd);",
    "//    Gui_ConsoleHwnd = NULL;",
]:
    require(branch, term, "Gui_ConsoleThread inactive taskbar branch")

for stale in [
    "this causes git.exe to hang",
    "jumplists for a console process are pointless anyways",
]:
    reject(branch, stale, "console taskbar comment")

for term in [
    "_FX void Taskbar_SetWindowAppUserModelId(HWND hwnd)",
    "SHGetPropertyStoreForWindow",
    "PKEY_AppUserModel_ID",
    "Taskbar_ShouldOverrideAppUserModelId",
    "Taskbar_SetProcessAppUserModelId",
]:
    require(taskbar, term, "taskbar.c owner adjacency")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "GUICON_CONSOLE_TASKBAR_INACTIVE_EDGE",
    "Gui_ConsoleThread",
    "Taskbar_SetWindowAppUserModelId",
    "SHGetPropertyStoreForWindow",
    "AppUserModelID",
    "Jump List",
    "SREV-004",
    "SREV-076",
    "SREV-241",
]:
    require(spec, term, "spec")

for term in [
    "Taskbar AppUserModelID Hook Trades Crash For Leak",
    "WindowFlags",
    "SetCurrentProcessExplicitAppUserModelID",
]:
    require(srev_004, term, "SREV-004 adjacency")

for term in [
    "GUI_CONSOLE_THREAD_HANDOFF",
    "Gui_ConsoleThread",
    "worker owns the context",
    "main-thread wait handle",
]:
    require(srev_076, term, "SREV-076 adjacency")

for term in [
    "TASKBAR_HEADER_TOPOLOGY_CONTRACT",
    "Taskbar_SetWindowAppUserModelId",
    "runtime owner is `taskbar.c`, which owns Shell/AppUserModelID hooks",
    "gui.c / guidlg.c",
]:
    require(srev_241, term, "SREV-241 adjacency")

for term in [
    "### SREV-292: GuiCon Console Taskbar Inactive Edge",
    "GUICON_CONSOLE_TASKBAR_INACTIVE_EDGE",
    "srev-292-guicon-console-taskbar-inactive-edge.schema.json",
    "Sandboxie/core/dll/guicon.c",
    "Gui_ConsoleThread",
    "Taskbar_SetWindowAppUserModelId",
    "SREV-004",
    "SREV-076",
    "SREV-241",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-292 source gate passed")
