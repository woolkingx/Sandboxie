#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-165 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-165 failed: {label} still contains {needle!r}")


def section(text: str, start: str, end: str) -> str:
    start_index = text.index(start)
    end_index = text.index(end, start_index)
    return text[start_index:end_index]


schema = json.loads((ROOT / "docs/plan/srev-165-process-wire-string-bounds.schema.json").read_text())
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-165 failed: schema is not draft-07")
if schema.get("id") != "PROCESS_WIRE_STRING_BOUNDS":
    raise SystemExit("SREV-165 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "ProcessServer.cpp owns service-side validation for process broker wire strings",
    "ProcessWire.h lengths are WCHAR counts not byte counts",
    "a WCHAR count must be checked against PIPE_MAX_DATA_LEN divided by sizeof WCHAR before multiplying by sizeof WCHAR",
    "offset validation must prove ofs is not greater than MSG_HEADER length before computing available bytes",
    "validation must compare byte length against available bytes and must not depend on ofs plus byte length arithmetic",
    "RunUpdaterHandler must check HeapAlloc before writing to cmd",
    "Linux source gate is not Windows service runtime proof",
]:
    require(contracts, term, "schema")

header = (ROOT / "Sandboxie/core/svc/ProcessServer.h").read_text()
wire = (ROOT / "Sandboxie/core/svc/ProcessWire.h").read_text()
source = (ROOT / "Sandboxie/core/svc/ProcessServer.cpp").read_text()
spec = (ROOT / "docs/plan/srev-165-process-wire-string-bounds.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-165.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "WCHAR *RunSandboxedCopyString(MSG_HEADER *msg, ULONG ofs, ULONG len);",
    "MSG_HEADER *RunSandboxedHandler(MSG_HEADER *msg);",
    "MSG_HEADER *RunUpdaterHandler(MSG_HEADER *msg);",
]:
    require(header, term, "ProcessServer.h")

for term in [
    "struct tagPROCESS_RUN_SANDBOXED_REQ",
    "ULONG cmd_ofs;",
    "ULONG cmd_len;",
    "ULONG dir_ofs;",
    "ULONG dir_len;",
    "ULONG env_ofs;",
    "ULONG env_len;",
    "struct tagPROCESS_RUN_UPDATER",
]:
    require(wire, term, "ProcessWire.h")

copy_string = section(
    source,
    "WCHAR *ProcessServer::RunSandboxedCopyString(",
    "//---------------------------------------------------------------------------\n// RunSandboxedCopyDeviceMap",
)
for term in [
    "if (len > (PIPE_MAX_DATA_LEN / sizeof(WCHAR)))",
    "ULONG bytes = len * sizeof(WCHAR);",
    "if (ofs > msg->length)",
    "ULONG available = msg->length - ofs;",
    "bytes       <= PIPE_MAX_DATA_LEN",
    "bytes       <= available",
    "HeapAlloc(GetProcessHeap(), 0, bytes + sizeof(WCHAR))",
    "memcpy(buffer, (UCHAR *)msg + ofs, bytes);",
    "buffer[bytes / sizeof(WCHAR)] = L'\\0';",
]:
    require(copy_string, term, "RunSandboxedCopyString")
reject(copy_string, "len *= sizeof(WCHAR);", "pre-validation multiplication")
reject(copy_string, "(ofs + len) <=", "offset-plus-length validation")
reject(copy_string, "len + 4", "old allocation size")

updater = section(
    source,
    "MSG_HEADER *ProcessServer::RunUpdaterHandler(MSG_HEADER *msg)",
    "//---------------------------------------------------------------------------\n// GetPebString",
)
for term in [
    "if (req->cmd_len > (PIPE_MAX_DATA_LEN / sizeof(WCHAR)))",
    "ULONG cmd_bytes = req->cmd_len * sizeof(WCHAR);",
    "if (req->cmd_ofs > req->h.length)",
    "ULONG available = req->h.length - req->cmd_ofs;",
    "cmd_bytes     <= PIPE_MAX_DATA_LEN",
    "cmd_bytes     <= available",
    "if (! cmd)",
    "return SHORT_REPLY(ERROR_NOT_ENOUGH_MEMORY);",
    "memcpy(ptr, ((UCHAR *)&req->h) + req->cmd_ofs, cmd_bytes);",
    "ptr[req->cmd_len] = L'\\0';",
]:
    require(updater, term, "RunUpdaterHandler")
reject(updater, "(req->cmd_len * sizeof(WCHAR))", "raw updater count multiplication")
reject(updater, "req->cmd_ofs +", "offset-plus-length validation")

for term in [
    "### SREV-165: Process Wire String Bounds",
    "PROCESS_WIRE_STRING_BOUNDS",
    "srev-165-process-wire-string-bounds.schema.json",
    "Sandboxie/core/svc/ProcessServer.h",
    "Sandboxie/core/svc/ProcessServer.cpp",
    "Sandboxie/core/svc/ProcessWire.h",
    "RunSandboxedCopyString",
    "RunUpdaterHandler",
    "cmd_bytes",
    "ERROR_NOT_ENOUGH_MEMORY",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-165 schema/source gate passed")
