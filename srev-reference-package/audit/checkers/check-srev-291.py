#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-291 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-291 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-291-guicon-klwtblfs-parent-exit-owner.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-291 failed: schema is not draft-07")
if schema.get("id") != "GUICON_KLWTBLFS_PARENT_EXIT_OWNER":
    raise SystemExit("SREV-291 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/dll/guicon.c":
    raise SystemExit("SREV-291 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "Gui_InitConsole2 owns only the already-running klwtblfs parent-exit worker branch",
    "proc.c owns SandboxieDcomLaunch create-process blocking for klwtblfs.exe",
    "Proc_WaitForParentExit owns waiting for the parent and exiting when DoExitProcess is enabled",
    "SREV-076 owns normal console helper handoff and cleanup",
    "CreateThread failure must preserve the existing fall-through behavior",
    "this SREV changes comments and proof only",
]:
    require(contracts, term, "schema")

guicon = (ROOT / "Sandboxie/core/dll/guicon.c").read_text()
proc = (ROOT / "Sandboxie/core/dll/proc.c").read_text()
spec = (ROOT / "docs/plan/srev-291-guicon-klwtblfs-parent-exit-owner.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-291.md").read_text()
srev_076 = (ROOT / "docs/plan/ledger/srev-076.md").read_text()

start = guicon.index("_FX void Gui_InitConsole2(void)")
end = guicon.index("// start an auxiliary thread", start)
branch = guicon[start:end]

for term in [
    "SREV-291: klwtblfs.exe uses a voluntary parent-exit worker.",
    "proc.c owns the DcomLaunch create-process block;",
    "covers an already-running image by calling Proc_WaitForParentExit",
    "with DoExitProcess enabled.",
    "if (_wcsicmp(Dll_ImageName, L\"klwtblfs.exe\") == 0) {",
    "HANDLE ThreadHandle = CreateThread(NULL, 0, Proc_WaitForParentExit, (void *)1, 0, NULL);",
    "if (ThreadHandle)",
    "CloseHandle(ThreadHandle);",
]:
    require(branch, term, "Gui_InitConsole2 klwtblfs branch")

for stale in [
    "$Workaround$ - 3rd party fix",
    "hack:  the Kaspersky process",
    "protected from",
    "voluntarily when the parent ends",
]:
    reject(branch, stale, "klwtblfs source comment")

for term in [
    "Dll_ImageType == DLL_IMAGE_SANDBOXIE_DCOMLAUNCH",
    "wcsistr(lpApplicationName, L\"klwtblfs.exe\")",
    "Blocked start of klwtblfs.exe",
    "return TRUE;        // exit CreateProcessInternal",
]:
    require(proc, term, "proc.c DcomLaunch adjacency")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "GUICON_KLWTBLFS_PARENT_EXIT_OWNER",
    "Proc_WaitForParentExit",
    "DoExitProcess",
    "CreateThread",
    "CloseHandle",
    "SREV-076",
]:
    require(spec, term, "spec")

for term in [
    "GUI_CONSOLE_THREAD_HANDOFF",
    "Gui_InitConsole2",
    "worker owns the context",
    "main-thread wait handle",
]:
    require(srev_076, term, "SREV-076 adjacency")

for term in [
    "### SREV-291: GuiCon klwtblfs Parent-Exit Owner",
    "GUICON_KLWTBLFS_PARENT_EXIT_OWNER",
    "srev-291-guicon-klwtblfs-parent-exit-owner.schema.json",
    "Sandboxie/core/dll/guicon.c",
    "klwtblfs.exe",
    "Proc_WaitForParentExit",
    "SREV-076",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-291 source gate passed")
