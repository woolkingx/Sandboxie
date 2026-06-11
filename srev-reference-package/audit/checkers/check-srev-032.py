#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-032 failed: {label} missing {needle!r}")


schema = json.loads((ROOT / "docs/plan/srev-032-process-suspend-one.schema.json").read_text())
if schema.get("id") != "PROCESS_SUSPEND_RESUME_ONE":
    raise SystemExit("SREV-032 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "OpenProcess(PROCESS_SUSPEND_RESUME) must return a non-NULL handle",
    "NtSuspendProcess and NtResumeProcess receive only a valid opened process handle",
    "CloseHandle is called exactly once",
    "OpenProcess failure returns STATUS_INVALID_CID",
]:
    require(contracts, term, "schema")

src = (ROOT / "Sandboxie/core/svc/ProcessServer.cpp").read_text()
wire = (ROOT / "Sandboxie/core/svc/ProcessWire.h").read_text()
spec = (ROOT / "docs/plan/srev-032-process-suspend-one.md").read_text()
ledger = read_combined_ledger(ROOT)

handler_start = src.index("MSG_HEADER *ProcessServer::SuspendOneHandler")
handler_end = src.index("MSG_HEADER *ProcessServer::SuspendAllHandler")
handler = src[handler_start:handler_end]

for term in [
    "PROCESS_SUSPEND_RESUME_ONE_REQ",
    "if (req->h.length < sizeof(PROCESS_SUSPEND_RESUME_ONE_REQ))",
    "HANDLE hProcess = OpenProcess(PROCESS_SUSPEND_RESUME, FALSE, req->pid);",
    "if (! hProcess)",
    "return SHORT_REPLY(STATUS_INVALID_CID);",
    "status = NtSuspendProcess(hProcess);",
    "status = NtResumeProcess(hProcess);",
    "CloseHandle(hProcess);",
]:
    require(handler, term, "source")

open_pos = handler.index("HANDLE hProcess = OpenProcess(PROCESS_SUSPEND_RESUME, FALSE, req->pid);")
guard_pos = handler.index("if (! hProcess)", open_pos)
fail_pos = handler.index("return SHORT_REPLY(STATUS_INVALID_CID);", guard_pos)
suspend_pos = handler.index("status = NtSuspendProcess(hProcess);")
resume_pos = handler.index("status = NtResumeProcess(hProcess);")
close_pos = handler.index("CloseHandle(hProcess);")
if not (open_pos < guard_pos < fail_pos < suspend_pos < close_pos):
    raise SystemExit("SREV-032 failed: suspend handle order is wrong")
if not (guard_pos < resume_pos < close_pos):
    raise SystemExit("SREV-032 failed: resume handle order is wrong")

require(wire, "struct tagPROCESS_SUSPEND_RESUME_ONE_REQ", "wire")
require(wire, "ULONG pid;", "wire")
require(wire, "BOOLEAN suspend;", "wire")

for term in [
    "https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-openprocess",
    "https://learn.microsoft.com/en-us/windows/win32/api/handleapi/nf-handleapi-closehandle",
    "srev-032-process-suspend-one.schema.json",
]:
    require(spec, term, "spec")

for term in [
    "### SREV-032: SuspendOne Process Handle Shape",
    "STATUS_INVALID_CID",
    "srev-032-process-suspend-one.schema.json",
]:
    require(ledger, term, "ledger")

print("SREV-032 schema/source gate passed")
