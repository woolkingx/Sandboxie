#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-316 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-316 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-316-ntmarta-window-security-hook-selection.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-316 failed: schema is not draft-07")
if schema.get("id") != "NTMARTA_WINDOW_SECURITY_HOOK_SELECTION":
    raise SystemExit("SREV-316 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/dll/advapi.c":
    raise SystemExit("SREV-316 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "GetSecurityInfo and SetSecurityInfo are handle plus SE_OBJECT_TYPE security APIs",
    "SE_WINDOW_OBJECT means a local window station or desktop object",
    "CreateDesktopW with NULL security attributes inherits from the parent window station",
    "Ntmarta_Init owns only ntmarta hook selection and function-pointer publication",
    "Ntmarta_GetSecurityInfo fallback remains owned by SREV-116 and SREV-126",
    "Ntmarta_SetSecurityInfo Chrome null window-object bypass remains owned by SREV-252",
    "comments and proof only",
]:
    require(contracts, term, "schema")

advapi = (ROOT / "Sandboxie/core/dll/advapi.c").read_text()
ldr = (ROOT / "Sandboxie/core/dll/ldr.c").read_text()
guienum = (ROOT / "Sandboxie/core/dll/guienum.c").read_text()
spec = (ROOT / "docs/plan/srev-316-ntmarta-window-security-hook-selection.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-316.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "{ L\"ntmarta.dll\",           Ntmarta_Init,                   0}, // SREV-316: window-object security hook selection",
]:
    require(ldr, term, "loader registration")
reject(ldr, "ntmarta.dll\",           Ntmarta_Init,                   0}, // workaround for chrome and acrobat reader", "loader comment")

init_start = advapi.index("_FX BOOLEAN Ntmarta_Init(HMODULE module)")
init_end = advapi.index("//---------------------------------------------------------------------------\n// Ntmarta_GetSecurityInfo", init_start)
init = advapi[init_start:init_end]
for term in [
    "GETPROC2(GetSecurityInfo, );",
    "Config_GetSettingsForImageName_bool(L\"UseSbieDeskHack\", TRUE)",
    "Dll_ImageType == DLL_IMAGE_GOOGLE_CHROME",
    "Dll_ImageType == DLL_IMAGE_MOZILLA_FIREFOX",
    "Dll_ImageType == DLL_IMAGE_ACROBAT_READER",
    "!SbieApi_QueryConfBool(NULL, L\"OpenWndStation\", FALSE)",
    "GetSecurityInfo = __sys_Ntmarta_GetSecurityInfo;",
    "SREV-316: publish ntmarta GetSecurityInfo for the",
    "SREV-116/SREV-126 dummy window-station DACL fallback.",
    "Direct ntmarta hooking can recurse with the Advapi32 hook",
    "during delay loading, so keep hook installation narrow.",
    "#ifndef _WIN64",
    "if (Dll_ImageType == DLL_IMAGE_ACROBAT_READER) {",
    "Acrobat 2019 32-bit CreateDesktopW can require the",
    "ntmarta hook to drop the sandboxie restricted-token",
    "SBIEDLL_HOOK2(Ntmarta_, GetSecurityInfo);",
    "__sys_GetSecurityInfo = GetSecurityInfo;",
    "GETPROC2(SetSecurityInfo, );",
    "SREV-316: only publish ntmarta SetSecurityInfo as the Chrome",
    "SREV-252 fallback when Advapi32 did not resolve the API.",
    "if (Dll_ImageType == DLL_IMAGE_GOOGLE_CHROME) {",
    "SetSecurityInfo = __sys_Ntmarta_SetSecurityInfo;",
    "Direct hook installation can recurse through Advapi32 delay loading.",
    "//SBIEDLL_HOOK2(Ntmarta_,SetSecurityInfo);",
    "__sys_SetSecurityInfo = SetSecurityInfo;",
]:
    require(init, term, "Ntmarta_Init")
for stale in [
    "this hook conflicts with the AdvApi32 hook and causes infinite callbacks if delay loading.",
    "This hook is need for Adobe Acrobat version 2019.010.x",
    "Due to the risk of the stack overflow issue",
    "only need to hook if Advapi32!SetSecurityInfo can't be resolved",
]:
    reject(init, stale, "Ntmarta_Init comment")

get_start = advapi.index("_FX DWORD Ntmarta_GetSecurityInfo(")
get_end = advapi.index("#ifdef _WIN64", get_start)
get_block = advapi[get_start:get_end]
for term in [
    "__sys_Ntmarta_GetSecurityInfo(handle, ObjectType, SecurityInfo, ppsidOwner, ppsidGroup, ppDacl, ppSacl, ppSecurityDescriptor);",
    "if (rc && ObjectType == SE_WINDOW_OBJECT && SecurityInfo == DACL_SECURITY_INFORMATION && Gui_Dummy_WinSta)",
    "__sys_Ntmarta_GetSecurityInfo(Gui_Dummy_WinSta, ObjectType, SecurityInfo, ppsidOwner, ppsidGroup, ppDacl, ppSacl, ppSecurityDescriptor);",
]:
    require(get_block, term, "Ntmarta_GetSecurityInfo")

set_start = advapi.index("_FX DWORD Ntmarta_SetSecurityInfo(")
set_block = advapi[set_start:]
for term in [
    "Same Chrome null window-object security bypass as AdvApi_SetSecurityInfo.",
    "if ((Dll_ImageType == DLL_IMAGE_GOOGLE_CHROME) && (ObjectType == SE_WINDOW_OBJECT) && (handle == NULL))",
    "return 0;",
    "return __sys_Ntmarta_SetSecurityInfo(handle, ObjectType, SecurityInfo, psidOwner, psidGroup, pDacl, pSacl);",
]:
    require(set_block, term, "Ntmarta_SetSecurityInfo")

desktop_start = guienum.index("_FX HDESK Gui_CreateDesktopW(")
desktop_block = guienum[desktop_start:]
for term in [
    "Gui_Dummy_WinSta",
    "_SetProcessWindowStation(Gui_Dummy_WinSta);",
    "CreateDesktopW without a security context",
    "Ntmarta_GetSecurityInfo hook",
    "rc = __sys_CreateDesktopW(lpszDesktop, NULL, NULL, dwFlags, dwDesiredAccess, NULL);",
]:
    require(desktop_block, term, "Gui_CreateDesktopW adjacency")

for term in [
    "NTMARTA_WINDOW_SECURITY_HOOK_SELECTION",
    "SE_WINDOW_OBJECT as a local window-station or desktop object",
    "CreateDesktopW with NULL security attributes",
    "SREV-116",
    "SREV-126",
    "SREV-252",
    "No hook predicate",
    "Runtime gate: Windows Chrome/Acrobat desktop creation",
]:
    require(spec, term, "spec")

for term in [
    "### SREV-316: Ntmarta Window Security Hook Selection",
    "NTMARTA_WINDOW_SECURITY_HOOK_SELECTION",
    "srev-316-ntmarta-window-security-hook-selection.schema.json",
    "Sandboxie/core/dll/advapi.c",
    "Ntmarta_Init",
    "Gui_CreateDesktopW",
    "SE_WINDOW_OBJECT",
    "SREV-252",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-316 source gate passed")
