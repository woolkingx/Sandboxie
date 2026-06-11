#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-004 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-004 failed: {label} still contains {needle!r}")


schema = json.loads((ROOT / "docs/plan/srev-004-taskbar-appid-process-parameters.schema.json").read_text())
if schema.get("id") != "TASKBAR_APPID_PROCESS_PARAMETERS":
    raise SystemExit("SREV-004 failed: schema missing TASKBAR_APPID_PROCESS_PARAMETERS")

contracts = "\n".join(schema["contracts"])
for term in [
    "SetCurrentProcessExplicitAppUserModelID assigns an AppUserModelID",
    "RTL_USER_PROCESS_PARAMETERS layout outside ImagePathName/CommandLine is reserved",
    "Hack must save WindowFlags before clearing the 0x5000 bits",
    "Hack must restore the saved 0x5000 bits",
]:
    require(contracts, term, "schema contracts")

src = (ROOT / "Sandboxie/core/dll/taskbar.c").read_text()
spec = (ROOT / "docs/plan/srev-004-taskbar-appid-process-parameters.md").read_text()
ledger = read_combined_ledger(ROOT)

for term in [
    "SavedWindowFlags",
    "hr = __sys_SetCurrentProcessExplicitAppUserModelID(AppId)",
    "SavedWindowFlags & 0x5000",
]:
    require(src, term, "DLL source")

reject(src, "HACK ALERT", "DLL source")

save = src.find("SavedWindowFlags = ProcessParms->WindowFlags;")
clear = src.find("ProcessParms->WindowFlags &= ~0x5000;", save)
call = src.find("hr = __sys_SetCurrentProcessExplicitAppUserModelID(AppId);", clear)
restore = src.find("SavedWindowFlags & 0x5000", call)
if min(save, clear, call, restore) < 0 or not save < clear < call < restore:
    raise SystemExit("SREV-004 failed: save/clear/call/restore chain must be ordered")

returns = src.count("__sys_SetCurrentProcessExplicitAppUserModelID(AppId)")
if returns != 2:
    raise SystemExit(f"SREV-004 failed: expected 2 real-API call sites (null fallback + scoped), got {returns}")

for term in [
    "SetCurrentProcessExplicitAppUserModelID",
    "RTL_USER_PROCESS_PARAMETERS",
    "reserved",
]:
    require(spec, term, "spec")

require(ledger, "### SREV-004: Taskbar AppUserModelID Hook Trades Crash For Leak", "ledger")
require(ledger, "Sandboxie/core/dll/taskbar.c", "ledger")

print("SREV-004 schema/source gate passed")
