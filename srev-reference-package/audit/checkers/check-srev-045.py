#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-045 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-045 failed: {label} still contains {needle!r}")


schema = json.loads(
    (
        ROOT / "docs/plan/srev-045-syscall-open-handle-writeback.schema.json"
    ).read_text()
)
if schema.get("id") != "SYSCALL_OPEN_HANDLE_WRITEBACK":
    raise SystemExit("SREV-045 failed: wrong schema id")
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-045 failed: schema is not draft-07")

contracts = "\n".join(schema["contracts"])
for term in [
    "UserHandlePtr is a user HANDLE* output pointer",
    "sizeof(HANDLE) alignment",
    "NewHandle remains driver-owned after TLS restore",
    "must be closed with NtClose",
    "returns the original syscall status",
    "use the same writeback helper",
]:
    require(contracts, term, "schema")

for term in [
    "UserHandlePtr",
    "NewHandle",
    "OrigStatus",
]:
    require("\n".join(schema["properties"].keys()), term, "draft-07 properties")

src = (ROOT / "Sandboxie/core/drv/syscall_open.c").read_text()
spec = (
    ROOT / "docs/plan/srev-045-syscall-open-handle-writeback.md"
).read_text()
ledger = read_combined_ledger(ROOT)

helper_start = src.index("static NTSTATUS Syscall_WriteRestoredHandleToUser(")
helper_end = src.index("// Syscall_CheckObject", helper_start)
helper = src[helper_start:helper_end]

open_start = src.index("_FX NTSTATUS Syscall_OpenHandle(")
open_end = src.index("// Syscall_GetNextProcess", open_start)
open_handle = src[open_start:open_end]

next_start = src.index("_FX NTSTATUS Syscall_GetNextProcess(")
next_end = src.index("// Syscall_GetNextThread", next_start)
get_next = src[next_start:next_end]

dup_start = src.index("_FX NTSTATUS Syscall_DuplicateHandle(")
dup_end = src.index("// Syscall_DuplicateHandle_2", dup_start)
duplicate = src[dup_start:dup_end]

for term in [
    "static NTSTATUS Syscall_WriteRestoredHandleToUser(",
    "ProbeForWrite(UserHandlePtr, sizeof(HANDLE), sizeof(HANDLE));",
    "*UserHandlePtr = NewHandle;",
    "NtClose(NewHandle);",
    "status = STATUS_PROCESS_IS_TERMINATING;",
    "return status;",
]:
    require(helper, term, "writeback helper")

require(
    src,
    "ProbeForWrite(UserHandlePtr, sizeof(HANDLE), sizeof(HANDLE));",
    "Syscall_ReplaceTargetHandle",
)

for block, label in [
    (open_handle, "Syscall_OpenHandle"),
    (get_next, "Syscall_GetNextProcess"),
    (duplicate, "Syscall_DuplicateHandle"),
]:
    require(
        block,
        "status = Syscall_WriteRestoredHandleToUser(\n"
        "                                    UserHandlePtr, NewHandle, orig_status);",
        label,
    )

for term in [
    "ProbeForWrite(UserHandlePtr, sizeof(HANDLE), sizeof(UCHAR));",
    "if (UserHandlePtr)\n                *UserHandlePtr = NewHandle;",
]:
    reject(src, term, "source")

for term in [
    "https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-probeforwrite",
    "https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/nf-ntifs-ntclose",
    "srev-045-syscall-open-handle-writeback.schema.json",
]:
    require(spec, term, "spec")

for term in [
    "### SREV-045: Syscall Open Handle Writeback",
    "Syscall_WriteRestoredHandleToUser",
    "srev-045-syscall-open-handle-writeback.schema.json",
]:
    require(ledger, term, "ledger")

print("SREV-045 schema/source gate passed")
