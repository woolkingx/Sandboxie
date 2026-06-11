#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-340 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-340 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-340-syscall-getnextprocess-fallback-topology.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-340 failed: schema is not draft-07")
if schema.get("id") != "SYSCALL_GETNEXTPROCESS_FALLBACK_TOPOLOGY":
    raise SystemExit("SREV-340 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/drv/syscall_open.c":
    raise SystemExit("SREV-340 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "fallback process-handle filtering loop only when Obj_CallbackInstalled is false",
    "Obj_CallbackInstalled is true the native syscall path is allowed",
    "temporary TLS handle slot before native dispatch",
    "Rejected outside-box process handles are closed before the next enumeration attempt",
    "Accepted process handles are returned through Syscall_WriteRestoredHandleToUser",
    "No public Microsoft Learn NtGetNextProcess DDI page was found",
    "This SREV changes comments and proof only",
]:
    require(contracts, term, "schema")

syscall_open = (ROOT / "Sandboxie/core/drv/syscall_open.c").read_text()
spec = (ROOT / "docs/plan/srev-340-syscall-getnextprocess-fallback-topology.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-340.md").read_text()
srev_045 = (ROOT / "docs/plan/ledger/srev-045.md").read_text()

start = syscall_open.index("_FX NTSTATUS Syscall_GetNextProcess(")
end = syscall_open.index("//---------------------------------------------------------------------------\n// Syscall_GetNextThread", start)
block = syscall_open[start:end]

for term in [
    "if (Obj_CallbackInstalled)",
    "return Syscall_Invoke(syscall_entry, user_args);",
    "SREV-340: without ObCallbacks, enumerate with NtGetNextProcess",
    "close each rejected outside-box process handle before trying",
    "The syscall ABI remains a runtime-only gate.",
    "HANDLE OldHandle = (HANDLE)user_args[0];",
    "ACCESS_MASK DesiredAccess = (ACCESS_MASK)user_args[1];",
    "next:",
    "Syscall_ReplaceTargetHandle(",
    "status = Syscall_Invoke(syscall_entry, user_args);",
    "NewHandle = Syscall_RestoreTargetHandle(",
    "if (OldHandle != (HANDLE)user_args[0])",
    "NtClose((HANDLE)user_args[0]);",
    "ObReferenceObjectByHandle(NewHandle, 0, *PsProcessType, UserMode, &ProcessObject, NULL)",
    "Thread_CheckObject_Common(proc, ProcessObject, DesiredAccess, TRUE, FALSE)",
    "user_args[0] = (ULONG_PTR)NewHandle;",
    "goto next;",
    "Syscall_WriteRestoredHandleToUser(",
]:
    require(block, term, "Syscall_GetNextProcess fallback")

reject(block, "ToDo: make this syscall work", "GetNextProcess TODO")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "No public Microsoft Learn DDI page for `NtGetNextProcess` was found",
    "Windows runtime",
    "gate",
]:
    require(spec, term, "NtGetNextProcess public-doc gap")

for term in [
    "Syscall_WriteRestoredHandleToUser",
    "Syscall_GetNextProcess",
    "invalid/racing output pointer",
]:
    require(srev_045, term, "SREV-045 adjacency")

for term in [
    "### SREV-340: Syscall GetNextProcess Fallback Topology",
    "SYSCALL_GETNEXTPROCESS_FALLBACK_TOPOLOGY",
    "srev-340-syscall-getnextprocess-fallback-topology.schema.json",
    "Sandboxie/core/drv/syscall_open.c",
    "Syscall_GetNextProcess",
    "Obj_CallbackInstalled",
    "Thread_CheckObject_Common",
    "Syscall_WriteRestoredHandleToUser",
    "SREV-045",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-340 source gate passed")
