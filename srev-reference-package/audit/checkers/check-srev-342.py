#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-342 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-342 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-342-token-primary-kernel-handle-boundary.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-342 failed: schema is not draft-07")
if schema.get("id") != "TOKEN_PRIMARY_KERNEL_HANDLE_BOUNDARY":
    raise SystemExit("SREV-342 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/drv/token.c":
    raise SystemExit("SREV-342 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "conversion from token object pointer to kernel-only token handle",
    "PROCESS_ACCESS_TOKEN",
    "OBJ_KERNEL_HANDLE and KernelMode",
    "ProcessAccessToken private ABI shape remains a Windows runtime gate",
    "Driver Verifier kernel-handle checks",
    "close the opened kernel handles",
    "This SREV changes comments and proof only",
]:
    require(contracts, term, "schema")

token = (ROOT / "Sandboxie/core/drv/token.c").read_text()
spec = (ROOT / "docs/plan/srev-342-token-primary-kernel-handle-boundary.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-342.md").read_text()

handle_start = token.index("_FX NTSTATUS Token_AssignPrimaryHandle(")
handle_end = token.index("//---------------------------------------------------------------------------\n// Token_AssignPrimary", handle_start)
handle_block = token[handle_start:handle_end]

assign_start = token.index("_FX BOOLEAN Token_AssignPrimary(")
assign_end = token.index("//---------------------------------------------------------------------------\n// Token_ReplacePrimary", assign_start)
assign_block = token[assign_start:assign_end]

for term in [
    "status = ObOpenObjectByPointer(ProcessObject, OBJ_KERNEL_HANDLE,\n        NULL, 0, NULL, KernelMode, &ProcessHandle);",
    "SREV-342: ProcessAccessToken consumes a kernel-only token handle.",
    "Token_AssignPrimary opens TokenObject with OBJ_KERNEL_HANDLE before",
    "Driver Verifier's kernel-handle checks.",
    "PROCESS_ACCESS_TOKEN info;",
    "info.Token = TokenKernelHandle;",
    "info.Thread = NULL;",
    "ZwSetInformationProcess(ProcessHandle, ProcessAccessToken, &info, sizeof(info));",
    "ZwClose(ProcessHandle);",
]:
    require(handle_block, term, "Token_AssignPrimaryHandle")

for stale in [
    "driver verifier will crash if the token",
    "handle is not a kernel handle",
]:
    reject(handle_block, stale, "Driver Verifier comment")

for term in [
    "status = ObOpenObjectByPointer(TokenObject, OBJ_KERNEL_HANDLE,\n        NULL, 0, NULL, KernelMode, &TokenHandle);",
    "status = Token_AssignPrimaryHandle(\n            ProcessObject, TokenHandle, SessionId);",
    "ZwClose(TokenHandle);",
]:
    require(assign_block, term, "Token_AssignPrimary")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "No public Microsoft Learn page was found",
    "ProcessAccessToken",
    "Driver Verifier",
    "Windows 7",
]:
    require(spec, term, "spec official gap/runtime gate")

for term in [
    "### SREV-342: Token Primary Kernel Handle Boundary",
    "TOKEN_PRIMARY_KERNEL_HANDLE_BOUNDARY",
    "srev-342-token-primary-kernel-handle-boundary.schema.json",
    "Sandboxie/core/drv/token.c",
    "Token_AssignPrimary",
    "Token_AssignPrimaryHandle",
    "PROCESS_ACCESS_TOKEN",
    "OBJ_KERNEL_HANDLE",
    "Driver Verifier",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-342 source gate passed")
