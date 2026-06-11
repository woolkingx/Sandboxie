#!/usr/bin/env python3
import json
from pathlib import Path

from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-241 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-241 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-241-taskbar-header-topology.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-241 failed: schema is not draft-07")
if schema.get("id") != "TASKBAR_HEADER_TOPOLOGY_CONTRACT":
    raise SystemExit("SREV-241 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/dll/taskbar.h":
    raise SystemExit("SREV-241 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "declaration header for shell taskbar entry points",
    "taskbar.c owns the implementation hook installation AppUserModelID state",
    "sh.c gui.c and guidlg.c are legal local callers",
    "Taskbar_SHCore_Init is intentionally declared in dll.h not taskbar.h",
    "Behavior changes must target taskbar.c or the concrete caller loader owner",
    "SREV-004 and SREV-228 remain the concrete behavior owners",
]:
    require(contracts, term, "schema contract")

spec = (ROOT / "docs/plan/srev-241-taskbar-header-topology.md").read_text()
header = (ROOT / "Sandboxie/core/dll/taskbar.h").read_text()
taskbar = (ROOT / "Sandboxie/core/dll/taskbar.c").read_text()
sh = (ROOT / "Sandboxie/core/dll/sh.c").read_text()
gui = (ROOT / "Sandboxie/core/dll/gui.c").read_text()
guidlg = (ROOT / "Sandboxie/core/dll/guidlg.c").read_text()
ldr = (ROOT / "Sandboxie/core/dll/ldr.c").read_text()
dll_h = (ROOT / "Sandboxie/core/dll/dll.h").read_text()
vcxproj = (ROOT / "Sandboxie/core/dll/SboxDll.vcxproj").read_text()
filters = (ROOT / "Sandboxie/core/dll/SboxDll.vcxproj.filters").read_text()
srev004 = (ROOT / "docs/plan/srev-004-taskbar-appid-process-parameters.md").read_text()
srev228 = (ROOT / "docs/plan/srev-228-taskbar-property-store-query-interface.md").read_text()
ledger = read_combined_ledger(ROOT)
fragment = (ROOT / "docs/plan/ledger/srev-241.md").read_text()

for term in [
    "#ifndef _MY_TASKBAR_H",
    "#define _MY_TASKBAR_H",
    "BOOLEAN Taskbar_Init(HMODULE);",
    "void Taskbar_SetProcessAppUserModelId(void);",
    "void Taskbar_SetWindowAppUserModelId(HWND hwnd);",
    "#endif /* _MY_TASKBAR_H */",
]:
    require(header, term, "header declaration")

for forbidden in [
    "Taskbar_SHCore_Init",
    "SBIEDLL_HOOK",
    "SetCurrentProcessExplicitAppUserModelID",
    "GetCurrentProcessExplicitAppUserModelID",
    "SHGetPropertyStoreForWindow",
    "IPropertyStore",
    "PKEY_AppUserModel",
    "QueryInterface",
    "Vtbl",
    "Dll_Alloc",
    "SbieApi_QueryConf",
]:
    reject(header, forbidden, "runtime owner code in header")

for term in [
    '#include "taskbar.h"',
    "static BOOLEAN Taskbar_Init_2(HMODULE module);",
    "_FX BOOLEAN Taskbar_Init(HMODULE module)",
    "SBIEDLL_HOOK(Taskbar_,SHGetPropertyStoreForWindow);",
    "_FX BOOLEAN Taskbar_Init_2(HMODULE module)",
    "SBIEDLL_HOOK(Taskbar_,SetCurrentProcessExplicitAppUserModelID);",
    "SBIEDLL_HOOK(Taskbar_,GetCurrentProcessExplicitAppUserModelID);",
    "_FX BOOLEAN Taskbar_SHCore_Init(HMODULE module)",
    "_FX void Taskbar_SetProcessAppUserModelId(void)",
    "_FX void Taskbar_SetWindowAppUserModelId(HWND hwnd)",
    "Taskbar_SHGetPropertyStoreForWindow(",
    "Taskbar_Unknown_QueryInterface(",
    "Taskbar_IPropertyStore_SetValue(",
]:
    require(taskbar, term, "taskbar.c owner topology")

for term in [
    '#include "taskbar.h"',
    "if (! Taskbar_Init(module))",
]:
    require(sh, term, "sh.c shell init caller")

for term in [
    '#include "taskbar.h"',
    "Taskbar_SetProcessAppUserModelId();",
    "Taskbar_SetWindowAppUserModelId(hwndResult);",
]:
    require(gui, term, "gui.c window lifecycle caller")

for term in [
    '#include "taskbar.h"',
    "Taskbar_SetWindowAppUserModelId(hWnd);",
]:
    require(guidlg, term, "guidlg.c dialog lifecycle caller")

for term in [
    "Taskbar_SHCore_Init",
    '{ L"shcore.dll",            Taskbar_SHCore_Init,            0}',
]:
    require(ldr, term, "ldr.c SHCore loader edge")

require(dll_h, "BOOLEAN Taskbar_SHCore_Init(HMODULE hmodule);", "dll.h SHCore declaration")
reject(header, "BOOLEAN Taskbar_SHCore_Init(HMODULE hmodule);", "misplaced SHCore declaration")

for term in [
    '<ClCompile Include="taskbar.c" />',
    '<ClInclude Include="taskbar.h" />',
]:
    require(vcxproj, term, "SboxDll project item")

for term in [
    '<ClCompile Include="taskbar.c">',
    '<ClInclude Include="taskbar.h">',
]:
    require(filters, term, "SboxDll filters item")

for term in [
    "SetCurrentProcessExplicitAppUserModelID",
    "RTL_USER_PROCESS_PARAMETERS",
    "WindowFlags",
]:
    require(srev004, term, "SREV-004 official/local shape")

for term in [
    "IPropertyStore",
    "SHGetPropertyStoreForWindow",
    "QueryInterface",
    "QueryInterface(IID_IUnknown)",
]:
    require(srev228, term, "SREV-228 official/local shape")

for term in [
    "SREV-004: Taskbar AppUserModelID Hook Trades Crash For Leak",
    "owner: \"Sandboxie/core/dll/taskbar.c:384-392\"",
    "SREV-228: Taskbar Property Store QueryInterface Contract",
    "Sandboxie/core/dll/taskbar.c",
]:
    require(ledger, term, "existing taskbar owner coverage")

for term in [
    "No source patch",
    "declaration/topology header",
    "No new Windows/API runtime behavior is defined by this header",
    "Taskbar_SHCore_Init` is not declared by `taskbar.h`",
    "future",
    "concrete-owner SREV Windows gates",
]:
    require(spec, term, "spec classification")

for term in [
    "kind: srev-ledger-entry",
    "id: SREV-241",
    "owner: Sandboxie/core/dll/taskbar.h",
    "docs-only-source-topology-reviewed",
    "srev-241-taskbar-header-topology.schema.json",
    "check-srev-241.py",
]:
    require(fragment, term, "ledger fragment")
    require(ledger, term, "combined ledger")

print("SREV-241 source gate passed")
