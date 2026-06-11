#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-104 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-104 failed: {label} still contains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-104-token-sid-storage-copy-boundary.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-104 failed: schema is not draft-07")
if schema.get("id") != "TOKEN_SID_STORAGE_COPY_BOUNDARY":
    raise SystemExit("SREV-104 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "SID is variable-length",
    "RtlValidSid must validate both the token SID and SandboxieLogonSid before RtlLengthSid",
    "RtlLengthSid has undefined return value for invalid SIDs",
    "RtlCopySid copies a SID into a caller-allocated buffer",
    "TOKEN_USER identifies the token user through SID_AND_ATTRIBUTES",
    "TOKEN_GROUPS contains group SID_AND_ATTRIBUTES",
    "SeFilterToken returns a referenced filtered token object",
    "Token_IsSharedSid_W8 is a private offset-based classifier",
    "inline token SID rewrite must use RtlCopySid",
    "shared or too-small token SID storage must use pointer substitution",
]:
    require(contracts, term, "schema")

source = (ROOT / "Sandboxie/core/drv/token.c").read_text()
spec = (ROOT / "docs/plan/srev-104-token-sid-storage-copy-boundary.md").read_text()
ledger = read_combined_ledger(ROOT)

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "Token_RestrictHelper1",
    "PSID SidInToken = SidAndAttrsInToken->Sid;",
    "if (SidInToken && RtlValidSid(SidInToken))",
    "if (!RtlValidSid(proc->SandboxieLogonSid))",
    "ULONG TokenSidLength = RtlLengthSid(SidInToken);",
    "ULONG SandboxieSidLength = RtlLengthSid(proc->SandboxieLogonSid);",
    "Windows 8.1 token SID storage can either be inline",
    "Token_IsSharedSid_W8(TempNewTokenObject)",
    "TokenSidLength < SandboxieSidLength",
    "OrigTokenSid = SidAndAttrsInToken->Sid;",
    "SidAndAttrsInToken->Sid = proc->SandboxieLogonSid;",
    "status = RtlCopySid(",
    "TokenSidLength, SidInToken, proc->SandboxieLogonSid",
    "SidAndAttrsInToken->Sid = OrigTokenSid;",
    "ObDereferenceObject(TempNewTokenObject);",
]:
    require(source, term, "token.c source shape")

function_start = source.index("_FX void *Token_RestrictHelper1")
function_end = source.index("// Token_RestrictHelper2", function_start)
helper = source[function_start:function_end]

valid_token = helper.index("RtlValidSid(SidInToken)")
length_token = helper.index("RtlLengthSid(SidInToken)")
if valid_token > length_token:
    raise SystemExit("SREV-104 failed: token SID length calculated before validation")

valid_sandbox = helper.index("RtlValidSid(proc->SandboxieLogonSid)")
length_sandbox = helper.index("RtlLengthSid(proc->SandboxieLogonSid)")
if valid_sandbox > length_sandbox:
    raise SystemExit("SREV-104 failed: sandbox SID length calculated before validation")

copy = helper.index("RtlCopySid(")
substitute = helper.index("SidAndAttrsInToken->Sid = proc->SandboxieLogonSid;")
restore = helper.index("SidAndAttrsInToken->Sid = OrigTokenSid;")
if not (substitute < restore):
    raise SystemExit("SREV-104 failed: pointer substitution is not restored")
if helper.index("TokenSidLength < SandboxieSidLength") > copy:
    raise SystemExit("SREV-104 failed: capacity check appears after copy")

for stale in [
    "SidInToken[1]",
    "memcpy(SidInToken, proc->SandboxieLogonSid",
    "We can't call memcpy on this shared memory. Workaround is",
    "workaround not unlike the one for win 8",
]:
    reject(helper, stale, "Token_RestrictHelper1")

for term in [
    "### SREV-104: Token SID Storage Copy Boundary",
    "TOKEN_SID_STORAGE_COPY_BOUNDARY",
    "srev-104-token-sid-storage-copy-boundary.schema.json",
    "RtlCopySid(TokenSidLength, SidInToken, proc->SandboxieLogonSid)",
]:
    require(ledger, term, "ledger")

print("SREV-104 schema/source gate passed")
