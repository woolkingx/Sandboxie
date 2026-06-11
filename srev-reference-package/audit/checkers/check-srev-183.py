#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-183 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-183 failed: {label} still contains {needle!r}")


def assert_before(text: str, label: str, earlier: str, later: str) -> None:
    e = text.find(earlier)
    l = text.find(later)
    if e < 0 or l < 0 or e > l:
        raise SystemExit(f"SREV-183 failed: {label}")


schema = json.loads((ROOT / "docs/plan/srev-183-token-handle-dacl-status-gate.schema.json").read_text())
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-183 failed: schema is not draft-07")
if schema.get("id") != "TOKEN_HANDLE_DACL_STATUS_GATE":
    raise SystemExit("SREV-183 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/drv/token.c":
    raise SystemExit("SREV-183 failed: wrong owner")
if schema.get("reviewed_public_surface") != "Sandboxie/core/drv/token.h":
    raise SystemExit("SREV-183 failed: wrong public surface")

contracts = "\n".join(schema["contracts"])
for term in [
    "Token_FilterDacl owns the restricted-token DACL update route",
    "Token_SetHandleDacl builds an absolute security descriptor",
    "security descriptor construction DDIs return NTSTATUS",
    "fail closed before ZwSetSecurityObject",
    "requires the rebuilt ACL to be non-NULL",
    "DACL_SECURITY_INFORMATION",
    "Sandboxie/core/drv/token.h was reviewed",
    "does not change token filtering policy",
    "runtime proof is required",
]:
    require(contracts, term, "schema contracts")

token_c = (ROOT / "Sandboxie/core/drv/token.c").read_text()
token_h = (ROOT / "Sandboxie/core/drv/token.h").read_text()
spec = (ROOT / "docs/plan/srev-183-token-handle-dacl-status-gate.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-183.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

start = token_c.index("_FX NTSTATUS Token_SetHandleDacl(HANDLE Handle, ACL *Dacl)")
end = token_c.index("// Token_Restrict", start)
helper = token_c[start:end]

for term in [
    "NTSTATUS status;",
    "if (!Dacl)",
    "return STATUS_INVALID_ACL;",
    "status = RtlCreateSecurityDescriptor(sd, SECURITY_DESCRIPTOR_REVISION);",
    "if (!NT_SUCCESS(status))",
    "return status;",
    "status = RtlSetDaclSecurityDescriptor(sd, TRUE, Dacl, FALSE);",
    "return ZwSetSecurityObject(Handle, DACL_SECURITY_INFORMATION, sd);",
]:
    require(helper, term, "Token_SetHandleDacl")

assert_before(
    helper,
    "RtlCreateSecurityDescriptor status checked before RtlSetDaclSecurityDescriptor",
    "status = RtlCreateSecurityDescriptor(sd, SECURITY_DESCRIPTOR_REVISION);",
    "status = RtlSetDaclSecurityDescriptor(sd, TRUE, Dacl, FALSE);",
)
assert_before(
    helper,
    "RtlSetDaclSecurityDescriptor status checked before ZwSetSecurityObject",
    "status = RtlSetDaclSecurityDescriptor(sd, TRUE, Dacl, FALSE);",
    "return ZwSetSecurityObject(Handle, DACL_SECURITY_INFORMATION, sd);",
)

for stale in [
    "RtlCreateSecurityDescriptor(sd, SECURITY_DESCRIPTOR_REVISION);\n    RtlSetDaclSecurityDescriptor",
    "RtlSetDaclSecurityDescriptor(sd, TRUE, Dacl, FALSE);\n\n    return ZwSetSecurityObject",
]:
    reject(helper, stale, "unchecked descriptor construction")

for term in [
    "NTSTATUS Token_QuerySidString",
    "void *Token_Filter(void *TokenObject, ULONG DropRights, ULONG SessionId);",
    "void *Token_Restrict(",
    "NTSTATUS Token_AssignPrimaryHandle(",
]:
    require(token_h, term, "token public declaration surface")

for term in [
    "Token_FilterDacl",
    "Token_SetHandleDacl",
    "RtlCreateSecurityDescriptor",
    "RtlSetDaclSecurityDescriptor",
    "ZwSetSecurityObject",
    "NULL DACL",
    "Sandboxie/core/drv/token.c",
    "Sandboxie/core/drv/token.h",
]:
    require(spec, term, "spec")

for term in [
    "kind: srev-ledger-entry",
    "id: SREV-183",
    "owner: Sandboxie/core/drv/token.c",
    "spec: docs/plan/srev-183-token-handle-dacl-status-gate.md",
    "schema: docs/plan/srev-183-token-handle-dacl-status-gate.schema.json",
    "checker: docs/plan/check-srev-183.py",
]:
    require(ledger_fragment, term, "ledger fragment header")

for term in [
    "### SREV-183: Token Handle DACL Status Gate",
    "TOKEN_HANDLE_DACL_STATUS_GATE",
    "Sandboxie/core/drv/token.c",
    "Sandboxie/core/drv/token.h",
    "Token_SetHandleDacl",
    "STATUS_INVALID_ACL",
    "RtlCreateSecurityDescriptor",
    "RtlSetDaclSecurityDescriptor",
    "ZwSetSecurityObject",
]:
    require(ledger, term, "combined ledger")

print("SREV-183 schema/source gate passed")
