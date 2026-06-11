#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-110 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-110 failed: {label} still contains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-110-thread-impersonation-offset-boundary.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-110 failed: schema is not draft-07")
if schema.get("id") != "THREAD_IMPERSONATION_OFFSET_BOUNDARY":
    raise SystemExit("SREV-110 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "Thread_StoreThreadToken references the active impersonation token",
    "CopyOnOpen EffectiveOnly",
    "SecurityImpersonation replay level",
    "Thread_SetThreadToken replays a stored thread token",
    "PsImpersonateClient at SecurityIdentification first",
    "private dynamic-data owned state",
    "masked client-security pointer against TokenObject",
    "PS_IMPERSONATION_INFORMATION TokenObject",
    "STATUS_ACCESS_DENIED and logs MSG_1222 0x62",
    "must not replace the shim",
    "PASSIVE_LEVEL DDIs",
    "SecurityIdentification cannot impersonate",
]:
    require(contracts, term, "schema")

source = (ROOT / "Sandboxie/core/drv/thread.c").read_text()
header = (ROOT / "Sandboxie/core/drv/thread.h").read_text()
thread_token = (ROOT / "Sandboxie/core/drv/thread_token.c").read_text()
spec = (ROOT / "docs/plan/srev-110-thread-impersonation-offset-boundary.md").read_text()
ledger = read_combined_ledger(ROOT)

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "Sandboxie needs the original token to satisfy the syscall",
    "reverts the thread after dispatch",
    "The supported API can downgrade this",
    "path to SecurityIdentification",
    "compatibility shim calls",
    "ETHREAD client-security field",
    "If the dynamic",
    "offset cannot be verified against TokenObject",
    "path fails closed",
]:
    require(source, term, "thread.c source comment")

reject(source, "to work around this, we intentionally call PsImpersonateClient", "stale workaround wording")

for term in [
    "PsReferenceImpersonationToken(PsGetCurrentThread()",
    "&CopyOnOpen, &EffectiveOnly, &ImpersonationLevel",
    "TokenObject = InterlockedExchangePointer(",
    "&thrd->token_object, TokenObject",
    "thrd->token_CopyOnOpen = CopyOnOpen;",
    "thrd->token_EffectiveOnly = EffectiveOnly;",
    "thrd->token_ImpersonationLevel = SecurityImpersonation;",
    "if (TokenObject)",
    "ObDereferenceObject(TokenObject);",
    "Thread_SetThreadToken",
    "Thread_GetByThreadId(proc, 0)",
    "ObReferenceObject(TokenObject);",
    "TokenObject = proc->primary_token;",
    "Thread_MyImpersonateClient(PsGetCurrentThread(), TokenObject",
]:
    require(source, term, "token capture/replay topology")

for term in [
    "PsImpersonateClient(ThreadObject, TokenObject",
    "CopyOnOpen, EffectiveOnly, SecurityIdentification",
    "Dyndata_Config.ImpersonationData_offset",
    "PS_IMPERSONATION_INFORMATION",
    "if (ImpersonationInfo->TokenObject != TokenObject)",
    "ImpersonationInfo_offset = 0;",
    "ImpersonationInfo->ImpersonationLevel = ImpersonationLevel;",
    "if ((*ImpersonationInfo & ~7) != (ULONG_PTR)TokenObject)",
    "++ImpersonationInfo;",
    "*ImpersonationInfo = ((*ImpersonationInfo) & ~3)",
    "| (ImpersonationLevel & 3);",
    "status = STATUS_ACCESS_DENIED;",
    "Log_Status(MSG_1222, 0x62, STATUS_UNKNOWN_REVISION);",
]:
    require(source, term, "private offset topology")

if "PsImpersonateClient(ThreadObject, TokenObject,\n                        CopyOnOpen, EffectiveOnly, ImpersonationLevel)" in source:
    raise SystemExit("SREV-110 failed: direct SecurityImpersonation replacement detected")

for term in [
    "Thread_ClearThreadToken()",
    "PsImpersonateClient(PsGetCurrentThread(), NULL",
]:
    require(header, term, "thread.h clear topology")

for term in [
    "RevertToSelf operation",
    "TokenObject = InterlockedExchangePointer(",
]:
    require(thread_token, term, "thread_token.c revert topology")

for term in [
    "### SREV-110: Thread Impersonation Offset Boundary",
    "THREAD_IMPERSONATION_OFFSET_BOUNDARY",
    "srev-110-thread-impersonation-offset-boundary.schema.json",
    "Sandboxie/core/drv/thread.c",
    "Thread_MyImpersonateClient",
    "PsImpersonateClient",
    "Dyndata_Config.ImpersonationData_offset",
]:
    require(ledger, term, "ledger")

print("SREV-110 schema/source gate passed")
