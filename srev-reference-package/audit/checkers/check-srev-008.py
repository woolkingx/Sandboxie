#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-008 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-008 failed: {label} still contains {needle!r}")


schema = json.loads((ROOT / "docs/plan/srev-008-token-default-dacl-spec.schema.json").read_text())
if schema.get("id") != "TOKEN_DEFAULT_DACL_SHAPE":
    raise SystemExit("SREV-008 failed: schema missing TOKEN_DEFAULT_DACL_SHAPE")

src = (ROOT / "Sandboxie/core/svc/ProcessServer.cpp").read_text()
spec = (ROOT / "docs/plan/srev-008-token-default-dacl-spec.md").read_text()
ledger = read_combined_ledger(ROOT)

reject(src, "pAcl->AclSize +=", "service source")
reject(src, "pAcl->AclRevision", "service source")

for term in [
    "if (! pAcl)",
    "GetAclInformation(",
    "AclSizeInformation",
    "AclRevisionInformation",
    "HeapAlloc(GetProcessHeap(), 0, NewAclSize)",
    "InitializeAcl(",
    "GetAce(",
    "AddAce(",
    "ok = AddAccessAllowedAce",
    "pDacl->DefaultDacl = pNewAcl",
    "sizeof(TOKEN_DEFAULT_DACL) + NewAclSize",
    "HeapFree(GetProcessHeap(), 0, pNewAcl)",
]:
    require(src, term, "service source")

for term in ["TOKEN_DEFAULT_DACL", "ACL", "opaque", "DefaultDacl == NULL"]:
    require(spec, term, "spec")

require(ledger, "### SREV-008: Token Default DACL Mutation Manually Pre-Bumps ACL Size", "ledger")
require(ledger, "Sandboxie/core/svc/ProcessServer.cpp", "ledger")

print("SREV-008 schema/source gate passed")
