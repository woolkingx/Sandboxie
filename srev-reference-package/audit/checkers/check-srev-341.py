#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-341 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-341 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-341-thread-change-notify-token-status-sentinel.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-341 failed: schema is not draft-07")
if schema.get("id") != "THREAD_CHANGE_NOTIFY_TOKEN_STATUS_SENTINEL":
    raise SystemExit("SREV-341 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/drv/thread_token.c":
    raise SystemExit("SREV-341 failed: wrong owner")
if "Sandboxie/core/drv/syscall.c" not in schema.get("additional_owners", []):
    raise SystemExit("SREV-341 failed: missing syscall.c additional owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "STATUS_THREAD_NOT_IN_PROCESS producer",
    "current-thread SetInformationThread sentinel consumer",
    "Sandboxie-private status signal",
    "preserves impersonation across syscall return only for this current-thread change-notify-token request",
    "Normal primary-token syscall returns still clear temporary thread impersonation",
    "SREV-329 and SREV-333 own adjacent",
    "This SREV changes comments and proof only",
]:
    require(contracts, term, "schema")

thread_token = (ROOT / "Sandboxie/core/drv/thread_token.c").read_text()
syscall = (ROOT / "Sandboxie/core/drv/syscall.c").read_text()
gui = (ROOT / "Sandboxie/core/dll/gui.c").read_text()
spec = (ROOT / "docs/plan/srev-341-thread-change-notify-token-status-sentinel.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-341.md").read_text()
srev_329 = (ROOT / "docs/plan/ledger/srev-329.md").read_text()
srev_333 = (ROOT / "docs/plan/ledger/srev-333.md").read_text()

imp_start = thread_token.index("_FX NTSTATUS Thread_SetInformationThread_ImpersonationToken(")
imp_end = thread_token.index("//---------------------------------------------------------------------------\n// Thread_CheckTokenForImpersonation", imp_start)
imp_block = thread_token[imp_start:imp_end]

change_start = thread_token.index("_FX NTSTATUS Thread_SetInformationThread_ChangeNotifyToken(PROCESS *proc)")
change_end = thread_token.index("//---------------------------------------------------------------------------\n// Thread_InitAnonymousToken", change_start)
change_block = thread_token[change_start:change_end]

invoke_start = syscall.index("_FX NTSTATUS Syscall_Api_Invoke(PROCESS *proc, ULONG64 *parms)")
invoke_end = syscall.index("//---------------------------------------------------------------------------\n// Syscall_Api_Query", invoke_start)
invoke_block = syscall[invoke_start:invoke_end]

for term in [
    "InfoLength != sizeof(HANDLE)",
    "ProbeForRead(InfoBuffer, InfoLength, sizeof(UCHAR));",
    "MyTokenHandle = *(HANDLE *)InfoBuffer;",
    "ThreadHandle == NtCurrentThread()",
    "MyTokenHandle == NtCurrentThread()",
    "Thread_SetInformationThread_ChangeNotifyToken(proc)",
    "status == STATUS_THREAD_NOT_IN_PROCESS",
    "status == STATUS_ALREADY_COMMITTED",
]:
    require(imp_block, term, "Thread_SetInformationThread_ImpersonationToken")

for term in [
    "SREV-341: Syscall_Api_Invoke normally clears the thread token",
    "STATUS_THREAD_NOT_IN_PROCESS sentinel only for this current-thread",
    "change-notify-token path",
    "return to the caller with an active impersonation",
    "PsReferenceImpersonationToken(",
    "CurrentToken = proc->primary_token;",
    "Token_Restrict(\n                CurrentToken, DISABLE_MAX_PRIVILEGE, proc)",
    "Thread_MyImpersonateClient(",
    "SecurityImpersonation",
    "proc->change_notify_token_flag = TRUE;",
    "return STATUS_THREAD_NOT_IN_PROCESS;",
    "return STATUS_ALREADY_COMMITTED;",
]:
    require(change_block, term, "Thread_SetInformationThread_ChangeNotifyToken")

reject(change_block, "hack with special", "change-notify-token comment")

for term in [
    "SREV-341: only the current-thread SetInformationThread sentinel",
    "Thread_SetInformationThread_ChangeNotifyToken keeps impersonation",
    "if (status == STATUS_THREAD_NOT_IN_PROCESS",
    "entry == Syscall_SetInformationThread",
    "user_args[0] == (ULONG_PTR)NtCurrentThread()",
    "status = STATUS_SUCCESS;",
    "Thread_ClearThreadToken();",
]:
    require(invoke_block, term, "Syscall_Api_Invoke sentinel consumer")

for term in [
    "Thread_SetInformationThread_ChangeNotifyToken",
    "NtSetInformationThread(NtCurrentThread()",
]:
    require(gui, term, "GUI change-notify-token caller")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "private current-thread",
    "`ThreadImpersonationToken` signal",
    "STATUS_THREAD_NOT_IN_PROCESS",
    "Thread_ClearThreadToken",
    "Runtime gate:",
]:
    require(spec, term, "spec sentinel contract")

for term in [
    "SXS NtSetInformationThread Pass-Through Hook",
    "Thread_SetInformationThread_ChangeNotifyToken",
]:
    require(srev_329, term, "SREV-329 adjacency")

for term in [
    "Kaspersky/WOW64",
    "NtSetInformationThread",
    "SREV-329",
]:
    require(srev_333, term, "SREV-333 adjacency")

for term in [
    "### SREV-341: Thread Change Notify Token Status Sentinel",
    "THREAD_CHANGE_NOTIFY_TOKEN_STATUS_SENTINEL",
    "srev-341-thread-change-notify-token-status-sentinel.schema.json",
    "Sandboxie/core/drv/thread_token.c",
    "Sandboxie/core/drv/syscall.c",
    "STATUS_THREAD_NOT_IN_PROCESS",
    "Thread_SetInformationThread_ChangeNotifyToken",
    "Syscall_Api_Invoke",
    "SREV-329",
    "SREV-333",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-341 source gate passed")
