#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-157 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-157 failed: {label} still contains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-157-driverassist-sandboxie-sid-account-name-bounds.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-157 failed: schema is not draft-07")
if schema.get("id") != "DRIVERASSIST_SANDBOXIE_SID_ACCOUNT_NAME_BOUNDS":
    raise SystemExit("SREV-157 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "DriverAssist::GetSandboxieSID owns the service-side account string",
    "LookupAccountNameW receives a null-terminated account string",
    "Sandboxie\\BoxName",
    "bounded API using ARRAYSIZE(szUserName)",
    "failed or truncated account-name formatting returns false before LookupAccountNameW",
    "RtlCreateVirtualAccountSid returns NTSTATUS and must succeed before AddSidName receives pSID",
    "does not change SandboxieLogon policy LookupAccountNameW scope domain string or LSA mapping semantics",
    "Linux source gate is not Windows runtime proof",
]:
    require(contracts, term, "schema")

header = (ROOT / "Sandboxie/core/svc/DriverAssist.h").read_text()
source = (ROOT / "Sandboxie/core/svc/DriverAssistSid.cpp").read_text()
spec = (ROOT / "docs/plan/srev-157-driverassist-sandboxie-sid-account-name-bounds.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-157.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "bool GetSandboxieSID(const WCHAR* boxname, UCHAR* SandboxieLogonSid, DWORD dwSidSize);",
    "void InitSIDs();",
    "void CleanUpSIDs();",
]:
    require(header, term, "DriverAssist.h")

for term in [
    "#include <strsafe.h>",
    "bool DriverAssist::GetSandboxieSID",
    "SbieApi_QueryConfBool(boxname, L\"SandboxieLogon\", FALSE)",
    "WCHAR szUserName[256], szDomainName[256];",
    "HRESULT hr;",
    "StringCchPrintfW(szUserName, ARRAYSIZE(szUserName), L\"%s\\\\%s\", SANDBOXIE, boxname);",
    "StringCchPrintfW(szUserName, ARRAYSIZE(szUserName), L\"%s\", SANDBOXIE);",
    "if (FAILED(hr))",
    "return false;",
    "LookupAccountName(NULL, szUserName, pSID, &dwSidSize, szDomainName, &dwDomainSize, &snu)",
    "RtlInitUnicodeString(&Name, boxname ? boxname : SANDBOXIE);",
    "NTSTATUS status = RtlCreateVirtualAccountSid(&Name, SBIE_RID, pSID, &dwSidSize);",
    "if (! NT_SUCCESS(status))",
    "return NT_SUCCESS(AddSidName(pSID, SANDBOXIE, boxname));",
]:
    require(source, term, "DriverAssistSid.cpp")

reject(source, "wcscpy(szUserName, SANDBOXIE);", "unbounded account-name copy")
reject(source, "wcscat(szUserName,", "unbounded account-name append")
reject(source, "RtlCreateVirtualAccountSid(&Name, SBIE_RID, pSID, &dwSidSize);\n\n    return NT_SUCCESS(AddSidName", "ignored virtual SID status")

format_gate = source.index("if (FAILED(hr))")
lookup = source.index("if (LookupAccountName(NULL, szUserName")
create = source.index("NTSTATUS status = RtlCreateVirtualAccountSid")
create_gate = source.index("if (! NT_SUCCESS(status))", create)
add = source.index("return NT_SUCCESS(AddSidName")

if not (format_gate < lookup):
    raise SystemExit("SREV-157 failed: formatting failure gate is not before LookupAccountNameW")
if not (create < create_gate < add):
    raise SystemExit("SREV-157 failed: virtual SID status gate is not before AddSidName")

for term in [
    "### SREV-157: DriverAssist Sandboxie SID Account Name Bounds",
    "DRIVERASSIST_SANDBOXIE_SID_ACCOUNT_NAME_BOUNDS",
    "srev-157-driverassist-sandboxie-sid-account-name-bounds.schema.json",
    "Sandboxie/core/svc/DriverAssist.h",
    "Sandboxie/core/svc/DriverAssistSid.cpp",
    "GetSandboxieSID",
    "LookupAccountNameW",
    "StringCchPrintfW",
    "RtlCreateVirtualAccountSid",
    "AddSidName",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-157 schema/source gate passed")
