#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-002 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-002 failed: {label} still contains {needle!r}")


schema = json.loads((ROOT / "docs/plan/srev-002-legacy-password-hash.schema.json").read_text())
if schema.get("id") != "LEGACY_PASSWORD_SHA1_HEX_SHAPE":
    raise SystemExit("SREV-002 failed: schema missing LEGACY_PASSWORD_SHA1_HEX_SHAPE")

contracts = "\n".join(schema["contracts"])
for term in [
    "CryptCreateHash creates a hash object",
    "CryptGetHashParam(HP_HASHVAL)",
    "LegacyBug switch",
    "first checks the historical buggy shape",
    "SHA256/salt password writes remain the only set-password output path",
]:
    require(contracts, term, "schema contracts")

src = (ROOT / "Sandboxie/core/svc/sbieiniserver.cpp").read_text()
hdr = (ROOT / "Sandboxie/core/svc/sbieiniserver.h").read_text()
spec = (ROOT / "docs/plan/srev-002-legacy-password-hash.md").read_text()
ledger = read_combined_ledger(ROOT)

require(hdr, "bool LegacyBug = true", "service header")

for term in [
    "bool LegacyBug",
    "LegacyBug ? 8 : 4",
    "HashPassword(Password, buf2, false)",
    "HashPassword2(req->new_password",
]:
    require(src, term, "service source")

reject(src, "bug bug should be", "service source")

legacy = src.find("if (HashPassword(Password, buf2))")
canonical = src.find("HashPassword(Password, buf2, false)")
if legacy == -1 or canonical == -1 or not (legacy < canonical):
    raise SystemExit("SREV-002 failed: legacy SHA1 read must precede canonical SHA1 read")

for term in ["CryptCreateHash", "HP_HASHVAL", "LegacyBug"]:
    require(spec, term, "spec")

for term in [
    "### SREV-002: Legacy SHA1 Password Hash Comment Admits Nibble Bug",
    "Sandboxie/core/svc/sbieiniserver.cpp",
]:
    require(ledger, term, "ledger")

print("SREV-002 schema/source gate passed")
