#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-025 failed: {label} missing {needle!r}")


schema = json.loads((ROOT / "docs/plan/srev-025-samr-set-security-object.schema.json").read_text())
if schema.get("id") != "SAMR_SET_SECURITY_OBJECT_GATE":
    raise SystemExit("SREV-025 failed: schema missing SAMR_SET_SECURITY_OBJECT_GATE")

src = (ROOT / "Sandboxie/core/drv/ipc_sam.c").read_text()
spec = (ROOT / "docs/plan/srev-025-samr-set-security-object.md").read_text()
ledger = read_combined_ledger(ROOT)

if "fixme: SandboxieCrypto.exe needs this" in src:
    raise SystemExit("SREV-025 failed: old SamSetSecurityObject fixme remains")

case = "case 0x02: // SamrSetSecurityObject"
require(src, case, "driver source")

case_pos = src.index(case)
next_case_pos = src.index("case 0x09:", case_pos)
body = src[case_pos:next_case_pos]
for term in ["if (proc->image_sbie)", "break;"]:
    if term not in body:
        raise SystemExit(f"SREV-025 failed: opnum 2 body missing {term!r}")

for term in [
    "https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-samr/6666a066-58cf-4118-bf4b-dd54ed55ecf0",
    "security-descriptor update",
    "proc->image_sbie",
]:
    require(spec, term, "spec")

for term in [
    "### SREV-025: SAMR SetSecurityObject Needed By SandboxieCrypto Has No Trusted-Image Gate",
    "SamrSetSecurityObject",
    "proc->image_sbie",
]:
    require(ledger, term, "ledger")

print("SREV-025 schema/source gate passed")
