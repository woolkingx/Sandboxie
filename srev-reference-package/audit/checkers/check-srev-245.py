#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-245 failed: {label} missing {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-245-cred-ansi-enumeration-domain-read-boundary.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-245 failed: schema is not draft-07")
if schema.get("id") != "CRED_ANSI_ENUM_DOMAIN_BOUNDARY":
    raise SystemExit("SREV-245 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "cred.c owns local credential virtualization",
    "CredEnumerateA and CredReadDomainCredentialsA return ANSI credential-array output slots",
    "array of PCREDENTIALA pointers in one allocated return block",
    "convert ANSI inputs to the wide local owner path",
    "must not return PCREDENTIALW data through an ANSI API",
    "current direct ANSI passthrough remains a documented boundary gap",
]:
    require(contracts, term, "schema")

source = (ROOT / "Sandboxie/core/dll/cred.c").read_text()
spec = (ROOT / "docs/plan/srev-245-cred-ansi-enumeration-domain-read-boundary.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-245.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "_FX BOOL Cred_CredReadDomainCredentialsW(",
    "Cred_GetName(\n                                DomainName, TargetInfo->TargetName, 0)",
    "hr = IPStore_ReadItem(",
    "return __sys_CredReadDomainCredentialsW(",
    "_FX BOOL Cred_CredEnumerateW(",
    "hr = IPStore_EnumItems(",
    "if (wcsncmp(name, Cred_SimpleCred, 11) != 0)",
    "ok = __sys_CredEnumerateW(pFilter, Flags, pCount, ppCredentials);",
    "*ppCredentials = Cred_UnserializeN(mrshcreds, pCount);",
]:
    require(source, term, "wide owner path")

for term in [
    "_FX BOOL Cred_CredReadDomainCredentialsA(",
    "ANSI array virtualization is owned by SREV-245; keep native passthrough",
    "until a CredFree-compatible ANSI array conversion owner exists.",
    "SbieApi_Log(2205, L\"CredReadDomainCredentialsA\");",
    "return __sys_CredReadDomainCredentialsA(\n                                pTargetInfo, Flags, pCount, ppCredentials);",
    "_FX BOOL Cred_CredEnumerateA(",
    "//SbieApi_Log(2205, L\"CredEnumerateA\");",
    "return __sys_CredEnumerateA(pFilter, Flags, pCount, ppCredentials);",
]:
    require(source, term, "ANSI direct passthrough gap")

for term in [
    "SREV-034 fixes single `CREDENTIALA` / `CREDENTIALW` conversion block",
    "SREV-116 fixes Advapi/Cred hook typedef pointer-depth",
    "dedicated ANSI credential-array conversion",
    "PCREDENTIALA **",
    "CredFree",
]:
    require(spec, term, "spec local contract")

for term in [
    "### SREV-245: Credential ANSI Enumeration And Domain Read Boundary",
    "CRED_ANSI_ENUM_DOMAIN_BOUNDARY",
    "srev-245-cred-ansi-enumeration-domain-read-boundary.schema.json",
    "Sandboxie/core/dll/cred.c",
    "Cred_CredReadDomainCredentialsA",
    "Cred_CredEnumerateA",
    "direct ANSI passthrough",
    "ANSI single-block array conversion",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-245 source gate passed")
