#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-252 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-252 failed: {label} still contains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-252-advapi-window-object-security-bypass.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-252 failed: schema is not draft-07")
if schema.get("id") != "ADVAPI_WINDOW_OBJECT_SECURITY_BYPASS":
    raise SystemExit("SREV-252 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "object identified by a handle",
    "window stations and desktops",
    "Chrome SE_WINDOW_OBJECT calls with a null handle",
    "same bypass predicate until Windows Chrome runtime proof",
    "SREV-116 and SREV-126 adjacency",
    "does not change DACL mutation behavior",
]:
    require(contracts, term, "schema")

advapi = (ROOT / "Sandboxie/core/dll/advapi.c").read_text()
spec = (ROOT / "docs/plan/srev-252-advapi-window-object-security-bypass.md").read_text()
srev_116 = (ROOT / "docs/plan/srev-116-advapi-header-out-param-schema.md").read_text()
srev_126 = (ROOT / "docs/plan/srev-126-guienum-windowstation-handle-ownership.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-252.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "Chrome 38 can probe a null window-station/desktop security handle here;",
    "keep the compatibility bypass local to Chrome SE_WINDOW_OBJECT calls.",
    "Same Chrome null window-object security bypass as AdvApi_SetSecurityInfo.",
    "if ((Dll_ImageType == DLL_IMAGE_GOOGLE_CHROME) && (ObjectType == SE_WINDOW_OBJECT) && (handle == NULL))",
    "return 0;",
    "return __sys_SetSecurityInfo(handle, ObjectType, SecurityInfo, psidOwner, psidGroup, pDacl, pSacl);",
    "return __sys_Ntmarta_SetSecurityInfo(handle, ObjectType, SecurityInfo, psidOwner, psidGroup, pDacl, pSacl);",
    "if (rc && ObjectType == SE_WINDOW_OBJECT && SecurityInfo == DACL_SECURITY_INFORMATION && Gui_Dummy_WinSta)",
]:
    require(advapi, term, "advapi.c")

reject(advapi, "this is a HACK to get Chrome 38 to work", "advapi.c")
reject(advapi, "this is a HACK to get Chrome 38 to work.", "advapi.c")

for term in [
    "GetSecurityInfo",
    "window-station",
    "fallback behavior",
    "No hook selection, `SetSecurityInfo` behavior",
]:
    require(srev_116, term, "SREV-116 adjacency")

for term in [
    "Gui_Dummy_WinSta",
    "GetProcessWindowStation",
    "CreateWindowStationW/A fallback",
]:
    require(srev_126, term, "SREV-126 adjacency")

for term in [
    "### SREV-252: Advapi Window Object Security Bypass",
    "ADVAPI_WINDOW_OBJECT_SECURITY_BYPASS",
    "srev-252-advapi-window-object-security-bypass.schema.json",
    "Sandboxie/core/dll/advapi.c",
    "SetSecurityInfo",
    "GetSecurityInfo",
    "SE_WINDOW_OBJECT",
    "SREV-116",
    "SREV-126",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-252 source gate passed")
