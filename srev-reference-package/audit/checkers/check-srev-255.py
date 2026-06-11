#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-255 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-255 failed: {label} still contains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-255-cred-ansi-todo-boundary-comment.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-255 failed: schema is not draft-07")
if schema.get("id") != "CRED_ANSI_TODO_BOUNDARY_COMMENT":
    raise SystemExit("SREV-255 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "remain direct native passthroughs",
    "SREV-245",
    "CredFree-compatible ANSI array conversion owner",
    "does not change hook registration",
]:
    require(contracts, term, "schema")

source = (ROOT / "Sandboxie/core/dll/cred.c").read_text()
spec = (ROOT / "docs/plan/srev-255-cred-ansi-todo-boundary-comment.md").read_text()
srev_245 = (ROOT / "docs/plan/srev-245-cred-ansi-enumeration-domain-read-boundary.md").read_text()
srev_245_check = (ROOT / "docs/plan/check-srev-245.py").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-255.md").read_text()

start = source.index("_FX BOOL Cred_CredReadDomainCredentialsA(")
end = source.index("// Cred_CredEnumerateA", start)
domain_a = source[start:end]
start = source.index("_FX BOOL Cred_CredEnumerateA(")
enum_a = source[start:]

for block, label in [(domain_a, "Cred_CredReadDomainCredentialsA"), (enum_a, "Cred_CredEnumerateA")]:
    require(block, "ANSI array virtualization is owned by SREV-245; keep native passthrough", label)
    require(block, "until a CredFree-compatible ANSI array conversion owner exists.", label)
    reject(block, "// todo", label)

for term in [
    "return __sys_CredReadDomainCredentialsA(\n                                pTargetInfo, Flags, pCount, ppCredentials);",
    "return __sys_CredEnumerateA(pFilter, Flags, pCount, ppCredentials);",
]:
    require(source, term, "native passthrough")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")
    require(srev_245, term, "SREV-245 official reference")

for term in [
    "ANSI array virtualization is owned by SREV-245; keep native passthrough",
    "until a CredFree-compatible ANSI array conversion owner exists.",
]:
    require(srev_245_check, term, "SREV-245 checker adjacency")

for term in [
    "used to have two local `// todo` comments",
    "ANSI array conversion owner exists",
]:
    require(srev_245, term, "SREV-245 spec adjacency")

for term in [
    "### SREV-255: Credential ANSI Todo Boundary Comment",
    "CRED_ANSI_TODO_BOUNDARY_COMMENT",
    "srev-255-cred-ansi-todo-boundary-comment.schema.json",
    "Sandboxie/core/dll/cred.c",
    "Cred_CredReadDomainCredentialsA",
    "Cred_CredEnumerateA",
    "SREV-245",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-255 source gate passed")
