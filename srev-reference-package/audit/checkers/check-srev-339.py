#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-339 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-339 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-339-syscall-open-thread-wow64-client-id-probe.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-339 failed: schema is not draft-07")
if schema.get("id") != "SYSCALL_OPEN_THREAD_WOW64_CLIENT_ID_PROBE":
    raise SystemExit("SREV-339 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/drv/syscall_open.c":
    raise SystemExit("SREV-339 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "OpenThread THREAD_GET_CONTEXT plus THREAD_SET_CONTEXT compatibility downgrade",
    "exact THREAD_GET_CONTEXT | THREAD_SET_CONTEXT access mask",
    "CLIENT_ID pointer must be probed before reading UniqueProcess",
    "ProbeForRead and the UniqueProcess read must stay inside a local try/except block",
    "Invalid CLIENT_ID access returns the exception code before native syscall dispatch",
    "Process_IsSameBox receives a captured process id not a user pointer",
    "does not change handle replacement object validation or restored-handle writeback topology",
]:
    require(contracts, term, "schema")

syscall_open = (ROOT / "Sandboxie/core/drv/syscall_open.c").read_text()
syscall = (ROOT / "Sandboxie/core/drv/syscall.c").read_text()
process_util = (ROOT / "Sandboxie/core/drv/process_util.c").read_text()
spec = (ROOT / "docs/plan/srev-339-syscall-open-thread-wow64-client-id-probe.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-339.md").read_text()
srev_045 = (ROOT / "docs/plan/ledger/srev-045.md").read_text()
srev_333 = (ROOT / "docs/plan/ledger/srev-333.md").read_text()

open_start = syscall_open.index("_FX NTSTATUS Syscall_OpenHandle(")
open_end = syscall_open.index("//---------------------------------------------------------------------------\n// Syscall_GetNextProcess", open_start)
open_block = syscall_open[open_start:open_end]

for term in [
    "SREV-339: Windows 10 1903+ WOW64 may open host threads for read",
    "THREAD_GET_CONTEXT",
    "THREAD_SET_CONTEXT",
    "caller-supplied CLIENT_ID safely",
    "if ((strcmp(syscall_entry->name, \"OpenThread\") == 0) && (user_args[1] == (THREAD_GET_CONTEXT | THREAD_SET_CONTEXT)))",
    "PCLIENT_ID  ClientId = (PCLIENT_ID)user_args[3];",
    "ULONG_PTR ClientProcessId = 0;",
    "__try {",
    "ProbeForRead(ClientId, sizeof(CLIENT_ID), sizeof(ULONG_PTR));",
    "ClientProcessId = (ULONG_PTR)ClientId->UniqueProcess;",
    "} __except (EXCEPTION_EXECUTE_HANDLER) {",
    "return GetExceptionCode();",
    "if ((ClientId == NULL) || !Process_IsSameBox(proc, NULL, ClientProcessId))",
    "user_args[1] = THREAD_GET_CONTEXT;",
    "Syscall_ReplaceTargetHandle(",
    "Syscall_Invoke(syscall_entry, user_args);",
    "Syscall_CheckObject(",
    "Syscall_WriteRestoredHandleToUser(",
]:
    require(open_block, term, "Syscall_OpenHandle OpenThread gate")

for stale in [
    "HACK ALERT! Starting in Win 10 1903",
    "The purpose is unknown at this time.",
    "So no hole is created.",
    "ClientId->UniqueProcess))",
]:
    reject(open_block, stale, "OpenThread WOW64 comment or direct read")

invoke_start = syscall.index("_FX NTSTATUS Syscall_Api_Invoke(PROCESS *proc, ULONG64 *parms)")
invoke_end = syscall.index("//---------------------------------------------------------------------------\n// Syscall_Api_Query", invoke_start)
invoke_block = syscall[invoke_start:invoke_end]
for term in [
    "user_args = (ULONG_PTR *)parms[2];",
    "ProbeForRead(user_args, args_len, sizeof(ULONG_PTR));",
    "status = entry->handler1_func(proc, entry, user_args);",
    "} __except (EXCEPTION_EXECUTE_HANDLER) {\n        status = GetExceptionCode();",
]:
    require(invoke_block, term, "Syscall_Api_Invoke adjacency")

samebox_start = process_util.index("_FX BOOLEAN Process_IsSameBox(")
samebox_end = process_util.index("//---------------------------------------------------------------------------\n// Process_IsStarter", samebox_start)
samebox_block = process_util[samebox_start:samebox_end]
for term in [
    "proc2 = Process_Find((HANDLE)(ULONG_PTR)proc2_pid, &irql);",
    "ok = FALSE;",
    "return ok;",
]:
    require(samebox_block, term, "Process_IsSameBox adjacency")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "Syscall_WriteRestoredHandleToUser",
    "Syscall_OpenHandle",
    "restored output boundary",
]:
    require(srev_045, term, "SREV-045 adjacency")

for term in [
    "Syscall_OpenHandle",
    "STATUS_BAD_INITIAL_PC",
    "WOW64",
]:
    require(srev_333, term, "SREV-333 adjacency")

for term in [
    "### SREV-339: Syscall OpenThread WOW64 ClientId Probe",
    "SYSCALL_OPEN_THREAD_WOW64_CLIENT_ID_PROBE",
    "srev-339-syscall-open-thread-wow64-client-id-probe.schema.json",
    "Sandboxie/core/drv/syscall_open.c",
    "OpenThread",
    "CLIENT_ID",
    "ProbeForRead",
    "Process_IsSameBox",
    "SREV-045",
    "SREV-333",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-339 source gate passed")
