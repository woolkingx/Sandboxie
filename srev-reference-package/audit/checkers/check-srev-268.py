#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-268 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-268 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-268-file-outlook-oice-everyone-sd-owner.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-268 failed: schema is not draft-07")
if schema.get("id") != "FILE_OUTLOOK_OICE_EVERYONE_SD_OWNER":
    raise SystemExit("SREV-268 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/dll/file.c":
    raise SystemExit("SREV-268 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "compatibility security-descriptor override for Outlook OICE_ previewer files",
    "Dll_ImageType is DLL_IMAGE_OFFICE_OUTLOOK",
    "Secure_EveryoneSD not a NULL DACL",
    "explicit local DACL that includes Authenticated Users and Everyone",
    "comments and proof only; Outlook previewer compatibility still needs Windows runtime proof",
]:
    require(contracts, term, "schema")

file_src = (ROOT / "Sandboxie/core/dll/file.c").read_text()
secure_src = (ROOT / "Sandboxie/core/dll/secure.c").read_text()
spec = (ROOT / "docs/plan/srev-268-file-outlook-oice-everyone-sd-owner.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-268.md").read_text()

start = file_src.index("if Microsoft Outlook 2010 is writing an OICE_ file")
end = file_src.index("otherwise we have to do the work", start)
outlook_block = file_src[start:end]

for term in [
    "SREV-268: Outlook OICE_ previewer files need the local public",
    "Secure_EveryoneSD compatibility descriptor",
    "Outlook image type and OICE_ path segment.",
    "Dll_ImageType == DLL_IMAGE_OFFICE_OUTLOOK",
    "wcsstr(TruePath, L\"\\\\OICE_\")",
    "objattrs.SecurityDescriptor = Secure_EveryoneSD;",
]:
    require(outlook_block, term, "Outlook OICE_ source block")

reject(outlook_block, "$Workaround$ - 3rd party fix", "Outlook OICE_ source block")

for term in [
    "PSECURITY_DESCRIPTOR Secure_EveryoneSD = NULL;",
    "AuthenticatedUsersSid",
    "EveryoneSid",
    "MyAllocAndInitSD(Secure_EveryoneSD);",
    "RtlSetDaclSecurityDescriptor(Secure_EveryoneSD, TRUE, MyAcl, FALSE);",
    "RtlSetSaclSecurityDescriptor(Secure_EveryoneSD, TRUE, MyAcl, FALSE);",
]:
    require(secure_src, term, "Secure_EveryoneSD construction")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "### SREV-268: File Outlook OICE Everyone SD Owner",
    "FILE_OUTLOOK_OICE_EVERYONE_SD_OWNER",
    "srev-268-file-outlook-oice-everyone-sd-owner.schema.json",
    "Sandboxie/core/dll/file.c",
    "Secure_EveryoneSD",
    "DLL_IMAGE_OFFICE_OUTLOOK",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-268 source gate passed")
