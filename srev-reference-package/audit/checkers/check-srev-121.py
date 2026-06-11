#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-121 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-121 failed: {label} still contains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-121-user-server-duplicate-handle-result-gate.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-121 failed: schema is not draft-07")
if schema.get("id") != "USER_SERVER_DUPLICATE_HANDLE_RESULT_GATE":
    raise SystemExit("SREV-121 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "DuplicateHandle returns a Win32 BOOL not an NTSTATUS",
    "DuplicateHandle success is nonzero and failure is zero",
    "StartWorker must not use NT_SUCCESS around DuplicateHandle",
    "StartWorker queues UserServer__APC only after DuplicateHandle succeeds",
    "StartWorker closes the duplicate handle if QueueUserAPC fails",
    "OpenFile initializes USER_OPEN_FILE_RPL FileHandle to zero before duplication",
    "OpenFile reports STATUS_UNSUCCESSFUL when DuplicateHandle into the caller process fails",
]:
    require(contracts, term, "schema")

source = (ROOT / "Sandboxie/core/svc/UserServer.cpp").read_text()
spec = (ROOT / "docs/plan/srev-121-user-server-duplicate-handle-result-gate.md").read_text()
ledger = read_combined_ledger(ROOT)

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

start_worker = source[
    source.index("ULONG UserServer::StartWorker"):
    source.index("// StartAsync")
]
for term in [
    "HANDLE hThis = NULL;",
    "if (DuplicateHandle(NtCurrentProcess(), NtCurrentProcess(), pi.hProcess, &hThis, SYNCHRONIZE, FALSE, 0)) {",
    "if (! QueueUserAPC(UserServer__APC, pi.hThread, (ULONG_PTR)hThis))",
    "CloseHandle(hThis);",
]:
    require(start_worker, term, "StartWorker")
reject(start_worker, "NT_SUCCESS(DuplicateHandle", "StartWorker old Win32 BOOL result gate")

open_file = source[
    source.index("ULONG UserServer::OpenFile"):
    source.index("ULONG UserServer::OpenDocument")
]
for term in [
    "rpl->FileHandle = 0;",
    "HANDLE hProcess = OpenProcess(PROCESS_DUP_HANDLE, FALSE, args->pid);",
    "if (! DuplicateHandle(NtCurrentProcess(), hFile, hProcess, (HANDLE*)&rpl->FileHandle, req->DesiredAccess, FALSE, 0))",
    "rpl->error = STATUS_UNSUCCESSFUL;",
    "CloseHandle(hProcess);",
    "NtClose(hFile);",
]:
    require(open_file, term, "OpenFile")
reject(open_file, "DuplicateHandle(NtCurrentProcess(), hFile, hProcess, (HANDLE*)&rpl->FileHandle, req->DesiredAccess, FALSE, 0);\n", "OpenFile ignored duplicate result")

for term in [
    "### SREV-121: User Server Duplicate Handle Result Gate",
    "USER_SERVER_DUPLICATE_HANDLE_RESULT_GATE",
    "srev-121-user-server-duplicate-handle-result-gate.schema.json",
    "Sandboxie/core/svc/UserServer.cpp",
    "DuplicateHandle",
    "QueueUserAPC",
    "OpenProcess",
    "STATUS_UNSUCCESSFUL",
    "USER_OPEN_FILE_RPL.FileHandle",
]:
    require(ledger, term, "ledger")

print("SREV-121 schema/source gate passed")
