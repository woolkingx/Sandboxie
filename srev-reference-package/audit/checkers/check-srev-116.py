#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-116 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-116 failed: {label} still contains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-116-advapi-header-out-param-schema.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-116 failed: schema is not draft-07")
if schema.get("id") != "ADVAPI_HEADER_OUT_PARAM_SCHEMA":
    raise SystemExit("SREV-116 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "advapi.h owns the hooked Advapi Cred function pointer shapes",
    "preserve pointer-depth for out parameters",
    "GetSecurityInfo receives PSID pointer output slots",
    "CredRead receives a credential output slot",
    "CredEnumerate receives a credential-array output slot",
    "hook implementation prototypes in advapi.c match",
    "does not change hook selection access masks",
]:
    require(contracts, term, "schema")

source_h = (ROOT / "Sandboxie/core/dll/advapi.h").read_text()
source_c = (ROOT / "Sandboxie/core/dll/advapi.c").read_text()
cred_c = (ROOT / "Sandboxie/core/dll/cred.c").read_text()
spec = (ROOT / "docs/plan/srev-116-advapi-header-out-param-schema.md").read_text()
ledger = read_combined_ledger(ROOT)

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

if source_h.count("typedef BOOL (*P_LookupAccountName)") != 1:
    raise SystemExit("SREV-116 failed: P_LookupAccountName typedef is not singular")

for term in [
    "typedef DWORD(*P_GetSecurityInfo)",
    "PSID *ppsidOwner",
    "PSID *ppsidGroup",
    "PACL *ppDacl",
    "PACL *ppSacl",
    "PSECURITY_DESCRIPTOR *ppSecurityDescriptor",
    "typedef BOOL(*P_CredRead)(",
    "void **ppCredential",
    "typedef BOOL(*P_CredEnumerate)(",
    "void ***ppCredential",
]:
    require(source_h, term, "advapi.h")

for stale in [
    "PSID psidOwner,\n    PSID psidGroup,\n    PACL pDacl,\n    PACL pSacl,\n    PSECURITY_DESCRIPTOR *ppSecurityDescriptor);",
    "const void *TargetName, ULONG Type, ULONG Flags, void *pCredential",
    "void *pFilter, ULONG Flags, ULONG *Count, void *ppCredential",
]:
    reject(source_h, stale, "advapi.h stale prototype")

for term in [
    "static DWORD AdvApi_GetSecurityInfo(",
    "_FX DWORD AdvApi_GetSecurityInfo(",
    "DWORD Ntmarta_GetSecurityInfo(",
    "_FX DWORD Ntmarta_GetSecurityInfo(",
    "PSID *ppsidOwner",
    "PSID *ppsidGroup",
    "PACL *ppDacl",
    "PACL *ppSacl",
    "__sys_GetSecurityInfo(handle, ObjectType, SecurityInfo, ppsidOwner, ppsidGroup, ppDacl, ppSacl, ppSecurityDescriptor)",
    "__sys_GetSecurityInfo(Gui_Dummy_WinSta, ObjectType, SecurityInfo, ppsidOwner, ppsidGroup, ppDacl, ppSacl, ppSecurityDescriptor)",
    "__sys_Ntmarta_GetSecurityInfo(handle, ObjectType, SecurityInfo, ppsidOwner, ppsidGroup, ppDacl, ppSacl, ppSecurityDescriptor)",
    "__sys_Ntmarta_GetSecurityInfo(Gui_Dummy_WinSta, ObjectType, SecurityInfo, ppsidOwner, ppsidGroup, ppDacl, ppSacl, ppSecurityDescriptor)",
]:
    require(source_c, term, "advapi.c")

for stale in [
    "__sys_GetSecurityInfo(handle, ObjectType, SecurityInfo, psidOwner, psidGroup, pDacl, pSacl, ppSecurityDescriptor)",
    "__sys_Ntmarta_GetSecurityInfo(handle, ObjectType, SecurityInfo, psidOwner, psidGroup, pDacl, pSacl, ppSecurityDescriptor)",
]:
    reject(source_c, stale, "advapi.c stale forwarding")

for term in [
    "static BOOL Cred_CredReadW(\n    const wchar_t *TargetName, ULONG Type, ULONG Flags, void **ppCredential);",
    "static BOOL Cred_CredReadA(\n    const char *TargetName, ULONG Type, ULONG Flags, void **ppCredential);",
    "static BOOL Cred_CredEnumerateW(\n    void *pFilter, ULONG Flags, ULONG *pCount, void ***ppCredentials);",
    "static BOOL Cred_CredEnumerateA(\n    void *pFilter, ULONG Flags, ULONG *pCount, void ***ppCredentials);",
    "__sys_CredReadW(TargetName, Type, Flags, ppCredential)",
    "__sys_CredEnumerateW(pFilter, Flags, pCount, ppCredentials)",
    "__sys_CredEnumerateA(pFilter, Flags, pCount, ppCredentials)",
]:
    require(cred_c, term, "cred.c consumer shape")

for term in [
    "### SREV-116: Advapi Header Out-Param Schema",
    "ADVAPI_HEADER_OUT_PARAM_SCHEMA",
    "srev-116-advapi-header-out-param-schema.schema.json",
    "Sandboxie/core/dll/advapi.h",
    "Sandboxie/core/dll/advapi.c",
    "Sandboxie/core/dll/cred.c",
    "PSID *",
    "PACL *",
    "void **ppCredential",
    "void ***ppCredential",
]:
    require(ledger, term, "ledger")

print("SREV-116 schema/source gate passed")
