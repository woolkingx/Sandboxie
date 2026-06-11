#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-087 failed: {label} missing {needle!r}")


def has_active_assignment(text: str, needle: str) -> bool:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("//"):
            continue
        if needle in stripped:
            return True
    return False


schema = json.loads(
    (ROOT / "docs/plan/srev-087-win32k-electron-workaround-boundary.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-087 failed: schema is not draft-07")
if schema.get("id") != "WIN32K_ELECTRON_WORKAROUND_BOUNDARY":
    raise SystemExit("SREV-087 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "local Sandboxie runtime state",
    "ProcessSystemCallDisablePolicy",
    "Direct3D runtime, UMD, KMD, and Dxgkrnl",
    "must not be toggled from a hook-installed boolean alone",
    "inactive Electron command-line workaround remains inactive",
    "does not extend win32u syscall patching",
]:
    require(contracts, term, "schema")

win32 = (ROOT / "Sandboxie/core/dll/Win32.c").read_text()
proc = (ROOT / "Sandboxie/core/dll/proc.c").read_text()
dllmain = (ROOT / "Sandboxie/core/dll/dllmain.c").read_text()
ldr = (ROOT / "Sandboxie/core/dll/ldr.c").read_text()
gui = (ROOT / "Sandboxie/core/dll/gui.c").read_text()
drv_syscall = (ROOT / "Sandboxie/core/drv/syscall.c").read_text()
process_api = (ROOT / "Sandboxie/core/drv/process_api.c").read_text()
spec = (ROOT / "docs/plan/srev-087-win32k-electron-workaround-boundary.md").read_text()
ledger = read_combined_ledger(ROOT)

for term in [
    "SBIE_FLAG_WIN32K_HOOKABLE",
    "EnableWin32kHooks",
    "UseWin32kHooks",
    "Win32_HookWin32WoW64();",
    "Win32_HookWin32SysCalls(hmodule);",
    "Electron GPU command-line handling stays inactive until a Windows",
    "runtime matrix proves win32k syscall hook coverage.",
]:
    require(win32, term, "Win32.c hook topology")

if has_active_assignment(win32, "Dll_ElectronWorkaround = FALSE"):
    raise SystemExit("SREV-087 failed: Win32_Init actively toggles Dll_ElectronWorkaround")

for term in [
    "//BOOL            Dll_ElectronWorkaround = FALSE;",
    "//Dll_ElectronWorkaround = Config_GetSettingsForImageName_bool",
    "Proc_IsLikelyElectronProcess",
    "//if (Dll_ElectronWorkaround)",
    "//        lpCommandLine = lpAlteredCommandLine;",
]:
    require(proc, term, "proc.c inactive Electron workaround evidence")

for term in [
    "Dll_TryDetectElectron",
    "UseElectronDetection",
]:
    require(dllmain, term, "dllmain.c Electron detection")

for term in [
    "Electron apps can have arbitrary names",
    "Dll_ImageType = DLL_IMAGE_GOOGLE_CHROME;",
]:
    require(ldr, term, "ldr.c dynamic Electron/Chrome classification")

for term in [
    "ProcessSystemCallDisablePolicy",
    "PROCESS_MITIGATION_SYSTEM_CALL_DISABLE_POLICY",
    "DisallowWin32kSystemCallsIsOn",
    "GetProcessMitigationPolicy",
]:
    require(gui, term, "gui.c public mitigation query")

for term in [
    "Syscall_Init_List32()",
    "Syscall_Init_Table32()",
]:
    require(drv_syscall, term, "driver win32k syscall table init")

for term in [
    "Syscall_MaxIndex32",
    "flags |= SBIE_FLAG_WIN32K_HOOKABLE;",
]:
    require(process_api, term, "process flag projection")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "### SREV-087: Win32k Electron Workaround Boundary",
    "WIN32K_ELECTRON_WORKAROUND_BOUNDARY",
    "srev-087-win32k-electron-workaround-boundary.schema.json",
]:
    require(ledger, term, "ledger")

print("SREV-087 schema/source gate passed")
