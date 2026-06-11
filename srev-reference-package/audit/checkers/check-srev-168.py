#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-168 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-168 failed: {label} still contains {needle!r}")


def section(text: str, start: str, end: str) -> str:
    start_index = text.index(start)
    end_index = text.index(end, start_index)
    return text[start_index:end_index]


schema = json.loads((ROOT / "docs/plan/srev-168-token-admin-membership-handle.schema.json").read_text())
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-168 failed: schema is not draft-07")
if schema.get("id") != "SBIEINI_TOKEN_ADMIN_MEMBERSHIP_HANDLE":
    raise SystemExit("SREV-168 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "sbieiniserver.h owns the exported service helper contract for TokenIsAdmin",
    "TokenIsAdmin must evaluate the supplied hToken instead of the service thread effective token",
    "primary tokens must be converted to an impersonation token before CheckTokenMembership",
    "duplicate tokens created for membership checking must be closed",
    "TokenElevationType remains queried from the original supplied token",
    "PipeServer::IsCallerAdmin must open caller process tokens with TOKEN_QUERY and TOKEN_DUPLICATE",
    "Linux source gate is not Windows service-token runtime proof",
]:
    require(contracts, term, "schema")

sbieini_h = (ROOT / "Sandboxie/core/svc/sbieiniserver.h").read_text()
sbieini_cpp = (ROOT / "Sandboxie/core/svc/sbieiniserver.cpp").read_text()
pipe_server = (ROOT / "Sandboxie/core/svc/PipeServer.cpp").read_text()
spec = (ROOT / "docs/plan/srev-168-token-admin-membership-handle.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-168.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

require(sbieini_h, "static bool TokenIsAdmin(HANDLE hToken, bool OnlyFull = false);", "sbieiniserver.h owner surface")

token_is_admin = section(
    sbieini_cpp,
    "bool SbieIniServer::TokenIsAdmin(HANDLE hToken, bool OnlyFull)",
    "//---------------------------------------------------------------------------\n// HashPassword",
)
for term in [
    "HANDLE hMembershipToken = hToken;",
    "HANDLE hDuplicateToken = NULL;",
    "TOKEN_TYPE tokenType;",
    "GetTokenInformation(",
    "hToken, TokenType, &tokenType, sizeof(tokenType), &len",
    "tokenType == TokenPrimary",
    "DuplicateToken(hToken, SecurityIdentification, &hDuplicateToken)",
    "hMembershipToken = hDuplicateToken;",
    "CheckTokenMembership(hMembershipToken, AdministratorsGroup, &b)",
    "CloseHandle(hDuplicateToken);",
    "hToken, (TOKEN_INFORMATION_CLASS)TokenElevationType",
]:
    require(token_is_admin, term, "TokenIsAdmin")
reject(token_is_admin, "CheckTokenMembership(NULL", "stale implicit-thread membership check")

is_caller_admin = section(
    pipe_server,
    "bool PipeServer::IsCallerAdmin()",
    "//---------------------------------------------------------------------------\n// IsCallerSigned",
)
for term in [
    "OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ",
    "OpenProcessToken(processHandle, TOKEN_QUERY | TOKEN_DUPLICATE, &hToken)",
    "SbieIniServer::TokenIsAdmin(hToken, true);",
    "CloseHandle(hToken);",
]:
    require(is_caller_admin, term, "PipeServer IsCallerAdmin")

for term in [
    "### SREV-168: Token Admin Membership Handle",
    "SBIEINI_TOKEN_ADMIN_MEMBERSHIP_HANDLE",
    "srev-168-token-admin-membership-handle.schema.json",
    "Sandboxie/core/svc/sbieiniserver.h",
    "Sandboxie/core/svc/sbieiniserver.cpp",
    "Sandboxie/core/svc/PipeServer.cpp",
    "TokenIsAdmin",
    "CheckTokenMembership",
    "DuplicateToken",
    "TOKEN_DUPLICATE",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-168 schema/source gate passed")
