#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-016 failed: {label} missing {needle!r}")


schema = json.loads((ROOT / "docs/plan/srev-016-accesscheckbytype-bypass.schema.json").read_text())
if schema.get("id") != "ACCESSCHECKBYTYPE_BYPASS_SHAPE":
    raise SystemExit("SREV-016 failed: schema missing ACCESSCHECKBYTYPE_BYPASS_SHAPE")

files = {
    "DLL advapi": (ROOT / "Sandboxie/core/dll/advapi.c").read_text(),
    "DLL secure": (ROOT / "Sandboxie/core/dll/secure.c").read_text(),
    "apps privs": (ROOT / "Sandboxie/apps/com/privs.h").read_text(),
}
spec = (ROOT / "docs/plan/srev-016-accesscheckbytype-bypass.md").read_text()
ledger = read_combined_ledger(ROOT)

for label, text in files.items():
    if "*GrantedAccess = 0xFFFFFFFF" in text:
        raise SystemExit(f"SREV-016 failed: {label} still grants 0xFFFFFFFF bypass")
    require(text, "DesiredAccess & MAXIMUM_ALLOWED", label)
    require(text, "GenericMapping->GenericAll", label)

secure = files["DLL secure"]
require(secure, "*AccessStatus = STATUS_SUCCESS", "DLL secure")
require(secure, "return STATUS_SUCCESS", "DLL secure")

for term in ["AccessCheckByType", "0xFFFFFFFF"]:
    require(spec, term, "spec")

require(ledger, "### SREV-016: AccessCheckByType Hook Grants Full Access As Compatibility Bypass", "ledger")
require(ledger, "Sandboxie/core/dll/advapi.c", "ledger")

print("SREV-016 schema/source gate passed")
