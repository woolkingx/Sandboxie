#!/usr/bin/env python3
import json
import re
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-009 failed: {label} missing {needle!r}")


schema = json.loads((ROOT / "docs/plan/srev-009-session0-token-spec.schema.json").read_text())
if schema.get("id") != "SESSION0_PRIMARY_TOKEN_SHAPE":
    raise SystemExit("SREV-009 failed: schema missing SESSION0_PRIMARY_TOKEN_SHAPE")

src = (ROOT / "Sandboxie/core/svc/ProcessServer.cpp").read_text()
spec = (ROOT / "docs/plan/srev-009-session0-token-spec.md").read_text()
ledger = read_combined_ledger(ROOT)

for term in [
    "HANDLE Session0PrimaryTokenHandle = NULL",
    "TOKEN_ASSIGN_PRIMARY | TOKEN_DUPLICATE | TOKEN_IMPERSONATE | TOKEN_QUERY",
    "PrimaryTokenHandle = Session0PrimaryTokenHandle",
    "if (Session0PrimaryTokenHandle)",
    "CloseHandle(Session0PrimaryTokenHandle)",
]:
    require(src, term, "service source")

start = src.find("RunSandboxedStartProcess")
end = src.find("RunSandboxedComServer", start) if start >= 0 else -1
region = src[start:end] if start >= 0 and end > 0 else ""
if re.search(r"^[ \t]*PrimaryTokenHandle = NULL;", region, re.M):
    raise SystemExit("SREV-009 failed: selected primary token is still nulled in RunSandboxedStartProcess")

assign = src.find("PrimaryTokenHandle = Session0PrimaryTokenHandle")
create = src.find("CreateProcessAsUser(\n                    PrimaryTokenHandle")
close = src.find("CloseHandle(Session0PrimaryTokenHandle)")
if min(assign, create, close) < 0 or not (assign < create < close):
    raise SystemExit("SREV-009 failed: session-0 primary token assign/create/close order broken")

for term in ["CreateProcessAsUserW", "DuplicateToken", "primary token"]:
    require(spec, term, "spec")

require(ledger, "### SREV-009: Session-0 Process Launch Token Is Nullified Before CreateProcessAsUser", "ledger")
require(ledger, "Sandboxie/core/svc/ProcessServer.cpp", "ledger")

print("SREV-009 schema/source gate passed")
