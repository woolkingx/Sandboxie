#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-044 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-044 failed: {label} still contains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-044-token-handle-writeback.schema.json").read_text()
)
if schema.get("id") != "TOKEN_HANDLE_WRITEBACK":
    raise SystemExit("SREV-044 failed: wrong schema id")
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-044 failed: schema is not draft-07")

contracts = "\n".join(schema["contracts"])
for term in [
    "TokenHandle is a user HANDLE* output pointer",
    "sizeof(HANDLE) alignment",
    "ownership remains driver-owned until written to TokenHandle",
    "must be closed with ZwClose and cleared",
    "successful writeback transfers handle ownership",
    "use the same writeback helper",
]:
    require(contracts, term, "schema")

for term in [
    "TokenHandle",
    "MyTokenHandle",
]:
    require("\n".join(schema["properties"].keys()), term, "draft-07 properties")

src = (ROOT / "Sandboxie/core/drv/thread_token.c").read_text()
spec = (ROOT / "docs/plan/srev-044-token-handle-writeback.md").read_text()
ledger = read_combined_ledger(ROOT)

helper_start = src.index("static NTSTATUS Thread_WriteTokenHandleToUser(")
helper_end = src.index("// Thread_OpenProcessToken", helper_start)
helper = src[helper_start:helper_end]

process_start = src.index("_FX NTSTATUS Thread_OpenProcessToken_Common(")
process_end = src.index("// Thread_SetInformationProcess", process_start)
process_common = src[process_start:process_end]

thread_start = src.index("_FX NTSTATUS Thread_OpenThreadToken_Common(")
thread_end = src.index("// Thread_OpenThreadToken_OpenHandle", thread_start)
thread_common = src[thread_start:thread_end]

for term in [
    "static NTSTATUS Thread_WriteTokenHandleToUser(",
    "ProbeForWrite(TokenHandle, sizeof(HANDLE), sizeof(HANDLE));",
    "*TokenHandle = *MyTokenHandle;",
    "ZwClose(*MyTokenHandle);",
    "*MyTokenHandle = NULL;",
]:
    require(helper, term, "writeback helper")

for block, label in [
    (process_common, "Thread_OpenProcessToken_Common"),
    (thread_common, "Thread_OpenThreadToken_Common"),
]:
    require(
        block,
        "ProbeForWrite(TokenHandle, sizeof(HANDLE), sizeof(HANDLE));",
        label,
    )
    require(
        block,
        "status = Thread_WriteTokenHandleToUser(TokenHandle, &MyTokenHandle);",
        label,
    )

for term in [
    "ProbeForWrite(TokenHandle, sizeof(HANDLE), sizeof(UCHAR));",
    "*TokenHandle = MyTokenHandle;",
]:
    reject(src, term, "source")

for term in [
    "https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-probeforwrite",
    "https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-zwclose",
    "srev-044-token-handle-writeback.schema.json",
]:
    require(spec, term, "spec")

for term in [
    "### SREV-044: Token Handle Writeback",
    "Thread_WriteTokenHandleToUser",
    "srev-044-token-handle-writeback.schema.json",
]:
    require(ledger, term, "ledger")

print("SREV-044 schema/source gate passed")
