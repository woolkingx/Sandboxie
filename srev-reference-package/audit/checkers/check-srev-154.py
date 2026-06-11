#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-154 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-154 failed: {label} still contains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-154-thread-token-parent-id-offset-fail-closed.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-154 failed: schema is not draft-07")
if schema.get("id") != "THREAD_TOKEN_PARENT_ID_OFFSET_FAIL_CLOSED":
    raise SystemExit("SREV-154 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "Thread_SetInformationProcess_PrimaryToken_3 mediates sandboxed child-process primary-token assignment",
    "TOKEN_STATISTICS.TokenId is the documented public token id source for TokenObject1",
    "SeQueryInformationToken returns a paged-pool buffer that must be freed with ExFreePool",
    "ParentTokenId is not exposed as a documented PACCESS_TOKEN field",
    "ParentTokenId_offset is private compatibility data",
    "unknown token private layout must log STATUS_UNKNOWN_REVISION dereference TokenObject2",
    "must not change SeAssignPrimaryTokenPrivilege SandboxieDcomLaunch.exe or msiexec.exe",
    "Linux source gate is not Windows runtime proof",
]:
    require(contracts, term, "schema")

source = (ROOT / "Sandboxie/core/drv/thread_token.c").read_text()
header = (ROOT / "Sandboxie/core/drv/thread.h").read_text()
spec = (ROOT / "docs/plan/srev-154-thread-token-parent-id-offset-fail-closed.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-154.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "void *token_object;",
    "BOOLEAN token_CopyOnOpen;",
    "BOOLEAN token_EffectiveOnly;",
    "SECURITY_IMPERSONATION_LEVEL token_ImpersonationLevel;",
    "Thread_ClearThreadToken()",
]:
    require(header, term, "thread.h token topology")

for term in [
    "Thread_SetInformationProcess_PrimaryToken_3",
    "PsReferenceImpersonationToken(PsGetCurrentThread()",
    "ULONG TokenId_offset = 0;",
    "ULONG ParentTokenId_offset = 0;",
    "PTOKEN_STATISTICS TokenStatistics1 = NULL;",
    "NTSTATUS status;",
    "TokenId_offset          = 0x10;",
    "ParentTokenId_offset    = 0x20;",
    "if ((! TokenId_offset) || (! ParentTokenId_offset)) {",
    "Log_Status(MSG_1222, 0x63, STATUS_UNKNOWN_REVISION);",
    "ObDereferenceObject(TokenObject2);",
    "return (void *)-1;",
    "SeQueryInformationToken(",
    "TokenObject1, TokenStatistics, &TokenStatistics1",
    "Log_Status(MSG_1222, 0x64, status);",
    "if (TokenStatistics1 && RtlEqualLuid(",
    "&TokenStatistics1->TokenId",
    "(LUID *)((ULONG_PTR)TokenObject2 + ParentTokenId_offset)",
    "ExFreePool(TokenStatistics1);",
    "TokenStatistics1 = NULL;",
    "Token_CheckPrivilege(",
    "SE_ASSIGNPRIMARYTOKEN_PRIVILEGE",
    "SANDBOXIE L\"DcomLaunch.exe\"",
    "L\"msiexec.exe\"",
]:
    require(source, term, "thread_token.c")

reject(
    source,
    "if (! TokenId_offset)\n        Log_Status(MSG_1222, 0x63, STATUS_UNKNOWN_REVISION);",
    "stale offset-zero continuation",
)
reject(
    source,
    "(LUID *)((ULONG_PTR)TokenObject1 + TokenId_offset)",
    "private TokenId field read",
)

unknown = source.index("if ((! TokenId_offset) || (! ParentTokenId_offset)) {")
first_compare = source.index("if (TokenStatistics1 && RtlEqualLuid(")
if unknown > first_compare:
    raise SystemExit("SREV-154 failed: private-offset fail-closed gate appears after first relation check")

unknown_block = source[unknown:first_compare]
for term in [
    "Log_Status(MSG_1222, 0x63, STATUS_UNKNOWN_REVISION);",
    "ObDereferenceObject(TokenObject2);",
    "return (void *)-1;",
]:
    require(unknown_block, term, "unknown-layout fail-closed block")

query = source.index("SeQueryInformationToken(")
free = source.index("ExFreePool(TokenStatistics1);", query)
if query > first_compare or free < first_compare:
    raise SystemExit("SREV-154 failed: TokenStatistics query/free ordering is wrong")

for term in [
    "### SREV-154: Thread Token ParentId Offset Fail Closed",
    "THREAD_TOKEN_PARENT_ID_OFFSET_FAIL_CLOSED",
    "srev-154-thread-token-parent-id-offset-fail-closed.schema.json",
    "Sandboxie/core/drv/thread.h",
    "Sandboxie/core/drv/thread_token.c",
    "Thread_SetInformationProcess_PrimaryToken_3",
    "SeQueryInformationToken",
    "TOKEN_STATISTICS.TokenId",
    "ParentTokenId_offset",
    "STATUS_UNKNOWN_REVISION",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-154 schema/source gate passed")
