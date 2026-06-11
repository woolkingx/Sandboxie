#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-315 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-315 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-315-scm-dll-service-start-shim.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-315 failed: schema is not draft-07")
if schema.get("id") != "SCM_DLL_SERVICE_START_SHIM":
    raise SystemExit("SREV-315 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/dll/scm_misc.c":
    raise SystemExit("SREV-315 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "DLL-triggered host service-start compatibility request",
    "dwrite.dll load to the FontCache service-start shim",
    "osppc.dll load to the osppsvc service-start shim",
    "boxed services must not be started",
    "StartServiceW success must not be treated as proof",
    "comments and proof only",
]:
    require(contracts, term, "schema")

scm_misc = (ROOT / "Sandboxie/core/dll/scm_misc.c").read_text()
ldr = (ROOT / "Sandboxie/core/dll/ldr.c").read_text()
spec = (ROOT / "docs/plan/srev-315-scm-dll-service-start-shim.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-315.md").read_text()

for term in [
    "{ L\"dwrite.dll\",            Scm_DWriteDll,                  0}, // SREV-315: DirectWrite FontCache service-start shim",
    "{ L\"osppc.dll\",             Scm_OsppcDll,                   0}, // ensure osppsvc is running",
]:
    require(ldr, term, "loader registration")

helper_start = scm_misc.index("_FX BOOLEAN Scm_DllHack(HMODULE module, const WCHAR *svcname)")
helper_end = scm_misc.index("//---------------------------------------------------------------------------\n// Scm_OsppcDll", helper_start)
helper = scm_misc[helper_start:helper_end]
for term in [
    "SREV-315: service-start compatibility shim.",
    "StartServiceW",
    "not that the",
    "service reached SERVICE_RUNNING",
    "if (! module)\n        return TRUE;",
    "if (Scm_IsBoxedService(svcname))\n        return TRUE;",
    "Scm_QueryServiceByName(svcname, TRUE, 0);",
    "if (state != SERVICE_STOPPED)\n        return TRUE;",
    "Scm_OpenServiceWImpl(\n                    HANDLE_SERVICE_MANAGER, svcname, SERVICE_START);",
    "if (Scm_StartServiceWImpl(hService, 0, NULL))\n            Sleep(500);",
    "Scm_CloseServiceHandleImpl(hService);",
]:
    require(helper, term, "Scm_DllHack")

for stale in [
    "hack:  make sure the given service is running",
]:
    reject(helper, stale, "Scm_DllHack comment")

ospp_start = scm_misc.index("_FX BOOLEAN Scm_OsppcDll(HMODULE module)")
ospp_end = scm_misc.index("//---------------------------------------------------------------------------\n// Scm_DWriteDll", ospp_start)
ospp = scm_misc[ospp_start:ospp_end]
for term in [
    "Custom_OsppcDll(module);",
    "Office 2010 osppc.dll compatibility shim for osppsvc startup.",
    "return Scm_DllHack(module, L\"osppsvc\");",
]:
    require(ospp, term, "Scm_OsppcDll")
reject(ospp, "hack for Office 2010", "osppc comment")

dwrite_start = scm_misc.index("_FX BOOLEAN Scm_DWriteDll(HMODULE module)")
dwrite_end = scm_misc.index("//---------------------------------------------------------------------------\n// Scm_Start_Sppsvc", dwrite_start)
dwrite = scm_misc[dwrite_start:dwrite_end]
for term in [
    "DirectWrite/IE 9 compatibility shim for FontCache startup.",
    "return Scm_DllHack(module, L\"FontCache\");",
]:
    require(dwrite, term, "Scm_DWriteDll")
reject(dwrite, "hack for IE 9", "dwrite comment")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "SCM_DLL_SERVICE_START_SHIM",
    "DirectWrite as providing font-system services",
    "StartServiceW only proves SCM accepted the start request",
    "No query, boxed-service skip, open access mask",
    "Runtime gate: Windows DirectWrite/IE 9 FontCache smoke",
]:
    require(spec, term, "spec")

for term in [
    "### SREV-315: SCM DLL Service Start Shim",
    "SCM_DLL_SERVICE_START_SHIM",
    "srev-315-scm-dll-service-start-shim.schema.json",
    "Sandboxie/core/dll/scm_misc.c",
    "Scm_DllHack",
    "Scm_DWriteDll",
    "FontCache",
    "SERVICE_RUNNING",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-315 source gate passed")
