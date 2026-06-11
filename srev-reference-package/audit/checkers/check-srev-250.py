#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-250 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-250 failed: {label} still contains {needle!r}")


def active_assignment(text: str, needle: str) -> bool:
    in_win32_init = False
    for line in text.splitlines():
        if "_FX BOOLEAN Win32_Init" in line:
            in_win32_init = True
        if in_win32_init and line.startswith("//---------------------------------------------------------------------------"):
            break
        stripped = line.strip()
        if in_win32_init and not stripped.startswith("//") and needle in stripped:
            return True
    return False


schema = json.loads(
    (ROOT / "docs/plan/srev-250-win32k-electron-comment-boundary.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-250 failed: schema is not draft-07")
if schema.get("id") != "WIN32K_ELECTRON_COMMENT_BOUNDARY":
    raise SystemExit("SREV-250 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "local Sandboxie runtime state not proof of Electron GPU compatibility",
    "remains inactive until Windows runtime matrix evidence",
    "proc.c Electron GPU command-line comments must name SREV-250",
    "Win32_Init must not assign Dll_ElectronWorkaround",
    "must not change win32k hook gates hook calls Electron detection or process creation behavior",
    "SREV-087 remains the behavior owner",
]:
    require(contracts, term, "schema")

win32 = (ROOT / "Sandboxie/core/dll/Win32.c").read_text()
proc = (ROOT / "Sandboxie/core/dll/proc.c").read_text()
srev_087 = (ROOT / "docs/plan/srev-087-win32k-electron-workaround-boundary.md").read_text()
srev_087_check = (ROOT / "docs/plan/check-srev-087.py").read_text()
spec = (ROOT / "docs/plan/srev-250-win32k-electron-comment-boundary.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-250.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")
    require(srev_087, term, "SREV-087 official reference")

for term in [
    "SBIE_FLAG_WIN32K_HOOKABLE",
    "EnableWin32kHooks",
    "UseWin32kHooks",
    "Win32_HookWin32WoW64();",
    "Win32_HookWin32SysCalls(hmodule);",
    "Electron GPU command-line handling stays inactive until a Windows",
    "runtime matrix proves win32k syscall hook coverage.",
]:
    require(win32, term, "Win32.c")

for term in [
    "Electron GPU command-line handling stays inactive until a Windows",
    "runtime matrix proves win32k syscall hook coverage.",
]:
    require(srev_087_check, term, "SREV-087 checker compatibility")

if active_assignment(win32, "Dll_ElectronWorkaround = FALSE"):
    raise SystemExit("SREV-250 failed: Win32_Init still actively assigns Dll_ElectronWorkaround")

reject(win32, "disable Electron Workaround when we are ready", "Win32.c stale comment")
reject(win32, "extern BOOL Dll_ElectronWorkaround;", "Win32.c stale commented declaration")
reject(win32, "Dll_ElectronWorkaround = FALSE;", "Win32.c stale commented assignment")

for term in [
    "SREV-250: Electron/Chromium process handling stays observation-only here.",
    "SREV-250: inactive Electron GPU command-line fallback.",
    "Runtime matrix proof is required before reviving mutation.",
    "//BOOL            Dll_ElectronWorkaround = FALSE;",
    "//Dll_ElectronWorkaround = Config_GetSettingsForImageName_bool",
    "Proc_IsLikelyElectronProcess",
    "//if (Dll_ElectronWorkaround)",
]:
    require(proc, term, "proc.c inactive Electron path remains owned by SREV-087")

proc_create_start = proc.index("_FX BOOL Proc_CreateProcessInternalW(")
proc_create_end = proc.index("if (Config_GetSettingsForImageName_bool(L\"DeprecatedTokenHacks\"", proc_create_start)
electron_block = proc[proc_create_start:proc_create_end]
for stale in [
    "$Workaround$ - 3rd party fix",
    "Hack: by adding a parameter to the gpu renderer process",
]:
    reject(electron_block, stale, "proc.c Electron anonymous workaround comment")

for term in [
    "SREV-250 later clarifies",
    "No behavior patch in this SREV",
]:
    require(srev_087, term, "SREV-087 adjacency")

for term in [
    "### SREV-250: Win32k Electron Comment Boundary",
    "WIN32K_ELECTRON_COMMENT_BOUNDARY",
    "srev-250-win32k-electron-comment-boundary.schema.json",
    "Sandboxie/core/dll/Win32.c",
    "SREV-087",
    "ProcessSystemCallDisablePolicy",
    "WDDM",
    "proc.c",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-250 source gate passed")
