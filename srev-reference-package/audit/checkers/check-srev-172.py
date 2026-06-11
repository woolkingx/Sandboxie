#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-172 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-172 failed: stale {label} still present")


def section(text: str, start: str, end: str) -> str:
    start_index = text.index(start)
    end_index = text.index(end, start_index)
    return text[start_index:end_index]


schema = json.loads((ROOT / "docs/plan/srev-172-setupapi-driver-install-status.schema.json").read_text())
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-172 failed: schema is not draft-07")
if schema.get("id") != "SETUPAPI_DRIVER_INSTALL_STATUS":
    raise SystemExit("SREV-172 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "setup.c owns SetupAPI catalog verification and CfgMgr32 driver package hook status projection",
    "VerifyCatalogFile result values are owned by the original SetupAPI function",
    "VerifyCatalogFile failure must not be converted into ERROR_SUCCESS",
    "CM_Add_Driver_PackageW and CM_Add_Driver_Package_ExW are blocked driver package install edges",
    "blocked driver package install must return a non success CONFIGRET",
    "CR_ACCESS_DENIED is the local blocked status for driver package hooks",
    "SREV-172 does not change hook installation message 2205 function pointer parameter count dynamic export lookup or disabled setup remove hooks",
    "Linux source gate is not Windows installer compatibility proof",
]:
    require(contracts, term, "schema")

setup_c = (ROOT / "Sandboxie/core/dll/setup.c").read_text()
ldr_c = (ROOT / "Sandboxie/core/dll/ldr.c").read_text()
dll_h = (ROOT / "Sandboxie/core/dll/dll.h").read_text()
spec = (ROOT / "docs/plan/srev-172-setupapi-driver-install-status.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-172.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "{ L\"cfgmgr32.dll\",          Setup_Init_CfgMgr32,            0}, // CM_Add_Driver_PackageW",
    "{ L\"setupapi.dll\",          Setup_Init_SetupApi,            0}, // VerifyCatalogFile",
]:
    require(ldr_c, term, "ldr.c hook registration")

for term in [
    "BOOLEAN Setup_Init_SetupApi(HMODULE);",
    "BOOLEAN Setup_Init_CfgMgr32(HMODULE);",
]:
    require(dll_h, term, "dll.h setup init prototypes")

for term in [
    "static ULONG Setup_VerifyCatalogFile(const WCHAR *CatalogFullPath);",
    "static ULONG Setup_CM_Add_Driver_PackageW(",
    "static ULONG Setup_CM_Add_Driver_Package_ExW(",
    "typedef ULONG (*P_VerifyCatalogFile)(const WCHAR *CatalogFullPath);",
    "typedef ULONG (*P_CM_Add_Driver_PackageW)(",
    "typedef ULONG (*P_CM_Add_Driver_Package_ExW)(",
    "FIND_EP(VerifyCatalogFile);",
    "DO_CALL_HOOK(VerifyCatalogFile,Setup_VerifyCatalogFile);",
    "FIND_EP(CM_Add_Driver_PackageW);",
    "FIND_EP(CM_Add_Driver_Package_ExW);",
    "DO_CALL_HOOK(\n            CM_Add_Driver_PackageW,Setup_CM_Add_Driver_PackageW);",
    "DO_CALL_HOOK(\n            CM_Add_Driver_Package_ExW,Setup_CM_Add_Driver_Package_ExW);",
    "#ifndef CR_ACCESS_DENIED",
    "#define CR_ACCESS_DENIED 0x00000033",
    "#define SETUP_CM_DRIVER_PACKAGE_BLOCKED_STATUS CR_ACCESS_DENIED",
]:
    require(setup_c, term, "setup.c owner surface")

verify = section(setup_c, "_FX ULONG Setup_VerifyCatalogFile(", "// Setup_SetupDiCallClassInstaller")
require(
    verify,
    "return __sys_VerifyCatalogFile(CatalogFullPath);",
    "VerifyCatalogFile status passthrough",
)
reject(verify, "SetLastError(0);", "catalog verification failure suppression")
reject(verify, "rc = 0;", "catalog verification success rewrite")
reject(verify, "rc != ERROR_AUTHENTICODE_TRUSTED_PUBLISHER", "trusted-publisher-only gate")

add_pkg = section(setup_c, "_FX ULONG Setup_CM_Add_Driver_PackageW(", "// Setup_CM_Add_Driver_Package_ExW")
add_pkg_ex = section(setup_c, "_FX ULONG Setup_CM_Add_Driver_Package_ExW(", "// Setup_CM_Add_Driver_Package_ExW\n//---------------------------------------------------------------------------\n\n\n/*static ULONG Setup_CM_Query")
for block, label, log_text in [
    (add_pkg, "CM_Add_Driver_PackageW", "CM Add Driver Package"),
    (add_pkg_ex, "CM_Add_Driver_Package_ExW", "CM Add Driver Package Ex"),
]:
    require(block, f"SbieApi_Log(2205, L\"{log_text}\");", label)
    require(block, "return SETUP_CM_DRIVER_PACKAGE_BLOCKED_STATUS;", label)
    reject(block, "return 0;", f"{label} false success")

for term in [
    "### SREV-172: SetupAPI Driver Install Status",
    "SETUPAPI_DRIVER_INSTALL_STATUS",
    "srev-172-setupapi-driver-install-status.schema.json",
    "Sandboxie/core/dll/setup.c",
    "Setup_VerifyCatalogFile",
    "CM_Add_Driver_PackageW",
    "CM_Add_Driver_Package_ExW",
    "CR_ACCESS_DENIED",
    "SBIE2205",
    "Windows DLL build",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-172 schema/source gate passed")
