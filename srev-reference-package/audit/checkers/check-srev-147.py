#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-147 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-147 failed: {label} still contains {needle!r}")


def function_body(text: str, name: str) -> str:
    marker = f"bool {name}("
    start = text.index(marker)
    next_marker = text.find("\n//---------------------------------------------------------------------------", start + len(marker))
    if next_marker == -1:
        return text[start:]
    return text[start:next_marker]


schema = json.loads(
    (ROOT / "docs/plan/srev-147-driverassist-log-token-user-buffer.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-147 failed: schema is not draft-07")
if schema.get("id") != "DRIVERASSIST_LOG_TOKEN_USER_BUFFER":
    raise SystemExit("SREV-147 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "GetUserNameFromProcess owns best-effort user-name enrichment for service log messages; failure must not block logging",
    "GetTokenInformation(TokenUser) writes a variable-size token-user structure and reports the required byte count through ReturnLength",
    "The local TokenUser stack buffer must be sized for sizeof(TOKEN_USER) + SECURITY_MAX_SID_SIZE, not a historical 64-byte guess",
    "LookupAccountSid mutates the userSize and domainSize in/out variables; post-call terminators must use the original caller-provided capacities",
    "Null or zero-sized caller buffers are invalid and must fail before any write",
]:
    require(contracts, term, "schema")

src = (ROOT / "Sandboxie/core/svc/DriverAssistLog.cpp").read_text()
spec = (ROOT / "docs/plan/srev-147-driverassist-log-token-user-buffer.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-147.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

body = function_body(src, "GetUserNameFromProcess")
for term in [
    "DWORD userCapacity = userSize;",
    "DWORD domainCapacity = domainSize;",
    "if (!user || !domain || !userCapacity || !domainCapacity)",
    "user[0] = L'\\0';",
    "domain[0] = L'\\0';",
    "BYTE data[sizeof(TOKEN_USER) + SECURITY_MAX_SID_SIZE];",
    "GetTokenInformation(hToken, TokenUser, data, tokenSize, &tokenSize)",
    "LookupAccountSid(NULL, pSID, user, &userSize, domain, &domainSize, &sidName)",
    "user[userCapacity - 1] = L'\\0';",
    "domain[domainCapacity - 1] = L'\\0';",
    "CloseHandle(hToken);",
]:
    require(body, term, "GetUserNameFromProcess")

for stale in [
    "BYTE data[64];",
    "needed 44 = sizeof(TOKEN_USER)",
    "user[userSize] = L'\\0';",
    "domain[domainSize] = L'\\0';",
]:
    reject(body, stale, "stale TokenUser buffer")

for term in [
    "WCHAR user[UNLEN + 1];",
    "WCHAR domain[DNLEN + 1];",
    "GetUserNameFromProcess(pid, user, UNLEN + 1, domain, DNLEN + 1)",
    "wsprintf(text2, L\"%s (%s\\\\%s)\", text, domain, user);",
]:
    require(src, term, "LogMessage_Single preservation")

for term in [
    "Sandboxie/core/svc/DriverAssistLog.cpp",
    "### SREV-147: DriverAssist Log Token User Buffer",
    "DRIVERASSIST_LOG_TOKEN_USER_BUFFER",
    "srev-147-driverassist-log-token-user-buffer.schema.json",
    "GetUserNameFromProcess",
    "GetTokenInformation",
    "LookupAccountSid",
    "SECURITY_MAX_SID_SIZE",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-147 schema/source gate passed")
