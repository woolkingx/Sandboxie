#!/usr/bin/env python3
import json
from pathlib import Path

from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-238 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-238 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-238-gui-driver-header-topology.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-238 failed: schema is not draft-07")
if schema.get("id") != "GUI_DRIVER_HEADER_TOPOLOGY_CONTRACT":
    raise SystemExit("SREV-238 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/drv/gui.h":
    raise SystemExit("SREV-238 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "driver GUI module declaration header",
    "module lifecycle process entry points",
    "does not own API handler registration XP win32k hook behavior OpenWinClass path policy",
    "Runtime behavior changes belong to gui.c gui_xp.c driver.c process.c",
    "driver initialization process lifecycle and GUI API topology",
]:
    require(contracts, term, "schema contract")

spec = (ROOT / "docs/plan/srev-238-gui-driver-header-topology.md").read_text()
header = (ROOT / "Sandboxie/core/drv/gui.h").read_text()
gui = (ROOT / "Sandboxie/core/drv/gui.c").read_text()
gui_xp = (ROOT / "Sandboxie/core/drv/gui_xp.c").read_text()
driver = (ROOT / "Sandboxie/core/drv/driver.c").read_text()
process = (ROOT / "Sandboxie/core/drv/process.c").read_text()
srev096_spec = (ROOT / "docs/plan/srev-096-clipboard-window-station-reference-owner.md").read_text()
srev134_spec = (ROOT / "docs/plan/srev-134-driverassist-clipboard-probe-hglobal-ownership.md").read_text()
ledger = read_combined_ledger(ROOT)
fragment = (ROOT / "docs/plan/ledger/srev-238.md").read_text()

for term in [
    '#include "driver.h"',
    "BOOLEAN Gui_Init(void);",
    "#ifdef XP_SUPPORT",
    "void Gui_Unload(void);",
    "BOOLEAN Gui_InitProcess(PROCESS *proc);",
    "void Gui_Check_OpenWinClass(PROCESS *proc);",
]:
    require(header, term, "header declaration")

for forbidden in [
    "Api_SetFunction",
    "Gui_Api_Clipboard",
    "Gui_Api_Init",
    "Process_GetPaths",
    "Process_AddPath",
    "Conf_Get",
    "PsGetProcessWin32WindowStation",
    "ObReferenceObjectByHandle",
    "Gui_InitClipboard",
    "Gui_FixClipboard",
    "Gui_Init_XpHook",
]:
    reject(header, forbidden, "runtime owner code in header")

for term in [
    '#include "gui.h"',
    "static NTSTATUS Gui_Api_Init(PROCESS *proc, ULONG64 *parms);",
    "static NTSTATUS Gui_Api_Clipboard(PROCESS *proc, ULONG64 *parms);",
    "_FX BOOLEAN Gui_Init(void)",
    "Api_SetFunction(API_INIT_GUI,       Gui_Api_Init);",
    "Api_SetFunction(API_GUI_CLIPBOARD,  Gui_Api_Clipboard);",
    "_FX NTSTATUS Gui_Api_Init(PROCESS *proc, ULONG64 *parms)",
    "_FX BOOLEAN Gui_InitProcess(PROCESS *proc)",
    "Process_GetPaths(",
    "Process_AddPath(proc, &proc->open_win_classes",
    "_FX void Gui_Check_OpenWinClass(PROCESS *proc)",
    "Conf_Get(proc->box->name, Gui_OpenClass_Name",
    "static BOOLEAN Gui_ReferenceClipboard(GUI_CLIPBOARD_REF *ref);",
    "_FX NTSTATUS Gui_Api_Clipboard(PROCESS *proc, ULONG64 *parms)",
    "PsGetProcessWin32WindowStation(PsGetCurrentProcess())",
    "ObReferenceObjectByHandle(",
]:
    require(gui, term, "gui.c owner topology")

for term in [
    "_FX BOOLEAN Gui_Init_XpHook(void)",
    "_FX NTSTATUS Gui_Api_Init_XpHook(PROCESS *proc, ULONG64 *parms)",
    "_FX void Gui_Unload_XpHook(void)",
]:
    require(gui_xp, term, "XP hook topology")

for term in [
    '#include "gui.h"',
    "ok = Gui_Init();",
    "#ifdef XP_SUPPORT",
    "Gui_Unload();",
]:
    require(driver, term, "driver lifecycle caller")

for term in [
    '#include "gui.h"',
    "Gui_Check_OpenWinClass(proc);",
    "if (!fail && !Gui_InitProcess(proc))",
]:
    require(process, term, "process lifecycle caller")

for term in [
    "SREV-096: Clipboard Window-Station Reference Owner",
    "owner: Sandboxie/core/drv/gui.c",
    "ObReferenceObjectByHandle",
    "Gui_InitClipboard",
    "SREV-134: DriverAssist Clipboard Probe HGLOBAL Ownership",
    "owner: Sandboxie/core/svc/DriverAssistStart.cpp",
    "DriverAssist::InitClipboard",
    "Sandboxie/core/drv/gui.c",
]:
    require(ledger, term, "existing GUI/clipboard owner coverage")

for term in [
    "window station",
    "ObReferenceObjectByHandle",
    "Gui_InitClipboard",
    "Gui_FixClipboard",
]:
    require(srev096_spec, term, "SREV-096 official shape")

for term in [
    "DriverAssist::InitClipboard",
    "GlobalAlloc",
    "SetClipboardData",
    "Gui_InitClipboard",
]:
    require(srev134_spec, term, "SREV-134 service probe shape")

for term in [
    "No source patch",
    "declaration/topology header",
    "No new Windows/API runtime behavior is defined by this header",
    "concrete-owner SREV Windows gates",
]:
    require(spec, term, "spec classification")

for term in [
    "kind: srev-ledger-entry",
    "id: SREV-238",
    "owner: Sandboxie/core/drv/gui.h",
    "docs-only-source-topology-reviewed",
    "srev-238-gui-driver-header-topology.schema.json",
    "check-srev-238.py",
]:
    require(fragment, term, "ledger fragment")
    require(ledger, term, "combined ledger")

print("SREV-238 source gate passed")
