#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-076 failed: {label} missing {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-076-gui-console-thread-handoff.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-076 failed: schema is not draft-07")
if schema.get("id") != "GUI_CONSOLE_THREAD_HANDOFF":
    raise SystemExit("SREV-076 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "allocated handle context exists before any handle slot write",
    "parent startup wait uses parent-owned ready-event and helper-thread handles",
    "worker owns the main-thread wait handle",
    "parent must not close a handle while the worker can still wait on it",
    "worker early exits and normal exit close the main-thread handle and free the context",
]:
    require(contracts, term, "schema")

src = (ROOT / "Sandboxie/core/dll/guicon.c").read_text()
spec = (ROOT / "docs/plan/srev-076-gui-console-thread-handoff.md").read_text()
ledger = read_combined_ledger(ROOT)

start = src.index("_FX void Gui_InitConsole2(void)")
thread_start = src.index("_FX ULONG Gui_ConsoleThread", start)
init_func = src[start:thread_start]
helper_start = src.index("_FX void Gui_FreeConsoleThreadHandles", thread_start)
thread_func = src[thread_start:helper_start]
helper_end = src.index("// Gui_SetConsoleTitleW", helper_start)
helper_func = src[helper_start:helper_end]

require(src, "static void Gui_FreeConsoleThreadHandles(HANDLE *Handles);", "source prototype")

for term in [
    "HANDLE ReadyEvent = NULL;",
    "HANDLE ConsoleThreadHandle = NULL;",
    "Handles = Dll_Alloc(2 * sizeof(HANDLE));",
    "if (! Handles)\n        return;",
    "Handles[0] = NULL;\n    Handles[1] = NULL;",
    "Handles[0] = OpenThread(SYNCHRONIZE, FALSE, GetCurrentThreadId());",
    "ReadyEvent = CreateEvent(NULL, FALSE, FALSE, NULL);",
    "Handles[1] = ReadyEvent;",
    "ConsoleThreadHandle = CreateThread(",
    "HANDLE WaitHandles[2] = { ReadyEvent, ConsoleThreadHandle };",
    "WaitForMultipleObjects(2, WaitHandles, FALSE, INFINITE);",
    "CloseHandle(ConsoleThreadHandle);",
    "Handles = NULL;",
    "CloseHandle(ReadyEvent);",
    "Gui_FreeConsoleThreadHandles(Handles);",
]:
    require(init_func, term, "Gui_InitConsole2 source")

for term in [
    "Gui_FreeConsoleThreadHandles(Handles);\n        return 0;",
    "SetEvent(Handles[1]);",
    "__sys_MsgWaitForMultipleObjects(\n                    1, Handles, FALSE, INFINITE, QS_ALLINPUT)",
    "Gui_FreeConsoleThreadHandles(Handles);\n    return 0;",
]:
    require(thread_func, term, "Gui_ConsoleThread source")

if thread_func.count("Gui_FreeConsoleThreadHandles(Handles);") < 3:
    raise SystemExit("SREV-076 failed: expected cleanup on import failure, window failure, and normal exit")

for term in [
    "if (Handles) {",
    "if (Handles[0])\n            CloseHandle(Handles[0]);",
    "Dll_Free(Handles);",
]:
    require(helper_func, term, "Gui_FreeConsoleThreadHandles source")

for stale in [
    "Dll_Alloc(3 * sizeof(HANDLE))",
    "\n            Handles[2]",
    "\n                CloseHandle(Handles[2])",
    "WaitForMultipleObjects(3, Handles",
]:
    if stale in init_func:
        raise SystemExit(f"SREV-076 failed: stale parent/worker mixed handle pattern remains: {stale}")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "### SREV-076: GUI Console Thread Handoff",
    "GUI_CONSOLE_THREAD_HANDOFF",
    "srev-076-gui-console-thread-handoff.schema.json",
]:
    require(ledger, term, "ledger")

print("SREV-076 schema/source gate passed")
