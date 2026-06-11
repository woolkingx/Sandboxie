#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-251 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-251 failed: {label} still contains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-251-advapi-change-notify-privilege-filter.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-251 failed: schema is not draft-07")
if schema.get("id") != "ADVAPI_CHANGE_NOTIFY_PRIVILEGE_FILTER":
    raise SystemExit("SREV-251 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "count plus optional array of privileges to delete",
    "LookupPrivilegeValueW resolves SE_CHANGE_NOTIFY_NAME",
    "traverse-checking bypass privilege",
    "may remove only that LUID",
    "lookup or scratch allocation fails",
    "does not change SID disabling restricted SID handling",
]:
    require(contracts, term, "schema")

advapi = (ROOT / "Sandboxie/core/dll/advapi.c").read_text()
spec = (ROOT / "docs/plan/srev-251-advapi-change-notify-privilege-filter.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-251.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "PLUID_AND_ATTRIBUTES privilegesToDeleteForCall = PrivilegesToDelete;",
    "DWORD   deletePrivilegeCountForCall = DeletePrivilegeCount;",
    "Chrome's dropped-rights token still needs traverse checking bypass",
    "semantics, so keep SeChangeNotifyPrivilege out of the delete list.",
    "if (DeletePrivilegeCount && PrivilegesToDelete",
    "&& __sys_LookupPrivilegeValueW(NULL, SE_CHANGE_NOTIFY_NAME, &luidChangeNotify))",
    "pModifiedPrivilegesToDelete = GlobalAlloc(GMEM_FIXED, sizeof(LUID_AND_ATTRIBUTES) * DeletePrivilegeCount);",
    "if (pModifiedPrivilegesToDelete) {",
    "for (i = 0, n = 0; i < DeletePrivilegeCount; i++)",
    "bChangeNotifyFound = TRUE;",
    "--dwModifiedDeletePrivilegeCount;",
    "deletePrivilegeCountForCall = dwModifiedDeletePrivilegeCount;",
    "privilegesToDeleteForCall = pModifiedPrivilegesToDelete;",
    "deletePrivilegeCountForCall, privilegesToDeleteForCall,",
]:
    require(advapi, term, "advapi.c")

reject(advapi, "This is a HACK to get Chrome 37 to work with dropped rights", "advapi.c")
reject(advapi, "for (i = 0; i < DeletePrivilegeCount; i++)\n    {\n        //wchar_t", "advapi.c stale outer loop")
reject(advapi, "__sys_LookupPrivilegeValueW(NULL, SE_CHANGE_NOTIFY_NAME, &luidChangeNotify);\n    pModifiedPrivilegesToDelete", "advapi.c unchecked lookup")

for term in [
    "DisableSidCount, SidsToDisable,",
    "RestrictedSidCount, SidsToRestrict,",
    "NewTokenHandle);",
    "if (pModifiedPrivilegesToDelete)",
    "GlobalFree(pModifiedPrivilegesToDelete);",
]:
    require(advapi, term, "unchanged token topology")

for term in [
    "### SREV-251: Advapi Change Notify Privilege Filter",
    "ADVAPI_CHANGE_NOTIFY_PRIVILEGE_FILTER",
    "srev-251-advapi-change-notify-privilege-filter.schema.json",
    "Sandboxie/core/dll/advapi.c",
    "CreateRestrictedToken",
    "LookupPrivilegeValueW",
    "SE_CHANGE_NOTIFY_NAME",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-251 source gate passed")
