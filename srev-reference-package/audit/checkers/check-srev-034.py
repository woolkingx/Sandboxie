#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-034 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-034 failed: {label} still contains {needle!r}")


schema = json.loads((ROOT / "docs/plan/srev-034-cred-aw-conversion.schema.json").read_text())
if schema.get("id") != "CRED_AW_CONVERSION_BLOCK":
    raise SystemExit("SREV-034 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "conversion output cursor starts inside the newly allocated output block",
    "Cred_CREDENTIALW2A must not write converted strings into the input CREDENTIALW block",
    "Cred_CopyW2A writes bytes through char*",
    "attribute array cursor advances by sizeof(CREDENTIAL_ATTRIBUTEA/W)",
]:
    require(contracts, term, "schema")

src = (ROOT / "Sandboxie/core/dll/cred.c").read_text()
spec = (ROOT / "docs/plan/srev-034-cred-aw-conversion.md").read_text()
ledger = read_combined_ledger(ROOT)

for term in [
    "char* strA = *pStrA;",
    "strA[i] = (char)strW[i];",
    "WCHAR* ptr = strW;",
    "if (! credW)",
    "sizeof(CREDENTIAL_ATTRIBUTEW) * credW->AttributeCount",
    "char* ptr = ((char*)credA) + sizeof(CREDENTIALA);",
    "if (! credA)",
    "sizeof(CREDENTIAL_ATTRIBUTEA) * credW->AttributeCount",
    "if (! TargetNameW)",
    "if (! *ppCredential)",
    "SetLastError(ERROR_NOT_ENOUGH_MEMORY);",
]:
    require(src, term, "source")

reject(src, "WCHAR* strA = *pStrA;", "source")
reject(src, "char* ptr = ((char*)credW) + sizeof(CREDENTIALW);", "source")
reject(src, "sizeof(PCREDENTIAL_ATTRIBUTEW) * credW->AttributeCount", "source")
reject(src, "sizeof(PCREDENTIAL_ATTRIBUTEA) * credW->AttributeCount", "source")

for term in [
    "https://learn.microsoft.com/en-us/windows/win32/api/wincred/ns-wincred-credentiala",
    "https://learn.microsoft.com/en-us/windows/win32/api/wincred/nf-wincred-credreada",
    "srev-034-cred-aw-conversion.schema.json",
]:
    require(spec, term, "spec")

for term in [
    "### SREV-034: Credential A/W Conversion Block Ownership",
    "Cred_CREDENTIALW2A",
    "srev-034-cred-aw-conversion.schema.json",
]:
    require(ledger, term, "ledger")

print("SREV-034 schema/source gate passed")
