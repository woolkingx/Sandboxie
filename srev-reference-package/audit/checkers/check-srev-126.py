#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-126 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-126 failed: {label} still contains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-126-guienum-windowstation-handle-ownership.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-126 failed: schema is not draft-07")
if schema.get("id") != "GUIENUM_WINDOWSTATION_HANDLE_OWNERSHIP":
    raise SystemExit("SREV-126 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "Gui_Dummy_WinSta is a process window-station handle captured from the process window-station topology",
    "GetProcessWindowStation returned handles are process-owned and must not be closed by ordinary callers",
    "CreateWindowStationW and CreateWindowStationA returned handles are caller-owned and releasable with CloseWindowStation",
    "CreateWindowStation fallback must not return Gui_Dummy_WinSta directly",
    "fallback returns a duplicate handle produced by DuplicateHandle in the current process with DUPLICATE_SAME_ACCESS",
    "duplicate inheritability follows SECURITY_ATTRIBUTES bInheritHandle when lpsa is supplied",
    "native CreateWindowStationW/A fallback policy predicates logging and failure return shape are unchanged",
]:
    require(contracts, term, "schema")

source = (ROOT / "Sandboxie/core/dll/guienum.c").read_text()
gui_source = (ROOT / "Sandboxie/core/dll/gui.c").read_text()
spec = (ROOT / "docs/plan/srev-126-guienum-windowstation-handle-ownership.md").read_text()
ledger = read_combined_ledger(ROOT)

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "Gui_Dummy_WinSta = _GetProcessWindowStation();",
    "_SetProcessWindowStation(\n                        (HWINSTA)rpl->hwinsta)",
]:
    require(gui_source, term, "Gui_Dummy_WinSta source topology")

create_w = source[
    source.index("_FX HANDLE Gui_CreateWindowStationW"):
    source.index("//Gui_CreateWindowStationA")
]
create_a = source[
    source.index("_FX HANDLE Gui_CreateWindowStationA"):
    source.index("// Gui_CreateDesktopW")
]

for label, block, proc in [
    ("CreateWindowStationW", create_w, "__sys_CreateWindowStationW"),
    ("CreateWindowStationA", create_a, "__sys_CreateWindowStationA"),
]:
    for term in [
        f"myHandle =  {proc}(lpwinsta, dwFlags, dwDesiredAccess, lpsa);",
        "if (myHandle)\n        return myHandle;",
        "extern HANDLE Gui_Dummy_WinSta;",
        "Config_GetSettingsForImageName_bool(L\"UseSbieWndStation\", TRUE)",
        "Dll_ImageType == DLL_IMAGE_GOOGLE_CHROME",
        "Dll_ImageType == DLL_IMAGE_MOZILLA_FIREFOX",
        "HANDLE hDuplicate = NULL;",
        "BOOL inherit = lpsa ? lpsa->bInheritHandle : FALSE;",
        "DuplicateHandle(GetCurrentProcess(), Gui_Dummy_WinSta,",
        "GetCurrentProcess(), &hDuplicate,",
        "0, inherit, DUPLICATE_SAME_ACCESS)",
        "return hDuplicate;",
        "SbieApi_Log(2205, L\"CreateWindowStation\");",
        "return 0;",
    ]:
        require(block, term, label)

    if block.index("DuplicateHandle(GetCurrentProcess(), Gui_Dummy_WinSta,") > block.index("SbieApi_Log(2205, L\"CreateWindowStation\");"):
        raise SystemExit(f"SREV-126 failed: {label} duplicate fallback is after failure log")
    reject(block, "return Gui_Dummy_WinSta;", label)

for term in [
    "### SREV-126: GUI Enum Window Station Handle Ownership",
    "GUIENUM_WINDOWSTATION_HANDLE_OWNERSHIP",
    "srev-126-guienum-windowstation-handle-ownership.schema.json",
    "Sandboxie/core/dll/guienum.c",
    "Gui_CreateWindowStationW",
    "Gui_CreateWindowStationA",
    "Gui_Dummy_WinSta",
    "GetProcessWindowStation",
    "CreateWindowStationW",
    "CloseWindowStation",
    "DuplicateHandle",
]:
    require(ledger, term, "ledger")

print("SREV-126 schema/source gate passed")
