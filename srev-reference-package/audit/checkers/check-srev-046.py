#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-046 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-046 failed: {label} still contains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-046-process-query-token-handle.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-046 failed: schema is not draft-07")
if schema.get("id") != "PROCESS_QUERY_TOKEN_HANDLE":
    raise SystemExit("SREV-046 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "info_data is a user ULONG64* output pointer",
    "token handle ownership remains driver-owned",
    "must be closed with NtClose and cleared",
    "thread token object lookup under proc->threads_lock",
    "after proc->threads_lock is released and IRQL is lowered",
    "same handle writeback helper",
]:
    require(contracts, term, "schema")

for term in [
    "info_data",
    "token_handle",
    "thread_token_lookup",
]:
    require("\n".join(schema["properties"].keys()), term, "draft-07 properties")

src = (ROOT / "Sandboxie/core/drv/process_api.c").read_text()
spec = (ROOT / "docs/plan/srev-046-process-query-token-handle.md").read_text()
ledger = read_combined_ledger(ROOT)

helper_start = src.index("static NTSTATUS Process_Api_WriteQueryUlong64ToUser(")
helper_end = src.index("_FX NTSTATUS Process_Api_QueryInfo(", helper_start)
helpers = src[helper_start:helper_end]

query_start = src.index("_FX NTSTATUS Process_Api_QueryInfo(")
query_end = src.index("// Process_Api_QueryBoxPath", query_start)
query = src[query_start:query_end]

itok_start = query.index("} else if (args->info_type.val == 'itok'")
itok_end = query.index("} else if (args->info_type.val == 'ippt'", itok_start)
itok = query[itok_start:itok_end]

lock_start = itok.index("ExAcquireResourceExclusiveLite(proc->threads_lock, TRUE);")
lock_end = itok.index("ExReleaseResourceLite(proc->threads_lock);")
locked_region = itok[lock_start:lock_end]
post_lock = itok[lock_end:]

for term in [
    "static NTSTATUS Process_Api_WriteQueryUlong64ToUser(",
    "ProbeForWrite(data, sizeof(ULONG64), sizeof(ULONG64));",
    "*data = value;",
    "static NTSTATUS Process_Api_WriteQueryHandleToUser(",
    "NtClose(*handle);",
    "*handle = NULL;",
]:
    require(helpers, term, "query writeback helpers")

for term in [
    "status = Process_Api_WriteQueryHandleToUser(\n"
    "                                                data, &MyTokenHandle);",
    "status = Process_Api_WriteQueryUlong64ToUser(\n"
    "                                                    data, token_present);",
    "status = Process_Api_WriteQueryHandleToUser(\n"
    "                                                    data, &MyTokenHandle);",
]:
    require(query, term, "Process_Api_QueryInfo")

for term in [
    "*data = (ULONG64)MyTokenHandle;",
    "*data = thrd->token_object ? TRUE : FALSE;",
]:
    reject(query, term, "Process_Api_QueryInfo")

for term in [
    "ObOpenObjectByPointer(",
    "Process_Api_WriteQueryUlong64ToUser(",
    "Process_Api_WriteQueryHandleToUser(",
]:
    reject(locked_region, term, "locked thread-token region")

for term in [
    "ObReferenceObject(ImpersonationTokenObject);",
    "ObOpenObjectByPointer(",
    "ObDereferenceObject(ImpersonationTokenObject);",
]:
    require(post_lock if term == "ObOpenObjectByPointer(" else itok, term, "thread-token routing")

for term in [
    "https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-probeforwrite",
    "https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/nf-ntifs-ntclose",
    "srev-046-process-query-token-handle.schema.json",
]:
    require(spec, term, "spec")

for term in [
    "### SREV-046: Process Query Token Handle",
    "Process_Api_WriteQueryHandleToUser",
    "srev-046-process-query-token-handle.schema.json",
]:
    require(ledger, term, "ledger")

print("SREV-046 schema/source gate passed")
