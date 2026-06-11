#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-151 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-151 failed: {label} still contains {needle!r}")


def between(text: str, start: str, end: str) -> str:
    a = text.index(start)
    b = text.index(end, a + len(start))
    return text[a:b]


schema = json.loads(
    (ROOT / "docs/plan/srev-151-namedpipe-read-reply-actual-length.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-151 failed: schema is not draft-07")
if schema.get("id") != "NAMEDPIPE_READ_REPLY_ACTUAL_LENGTH":
    raise SystemExit("SREV-151 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "read_len is the maximum requested byte count and caller buffer size",
    "IO_STATUS_BLOCK.Information is the completed read transfer count",
    "NAMED_PIPE_READ_RPL.data_len is the actual number of bytes present in the reply tail, not the requested maximum",
    "Completed read replies must satisfy data_len <= read_len and FIELD_OFFSET(NAMED_PIPE_READ_RPL, data) + data_len <= h.length, even when the completion status is a warning such as a partial message transfer",
    "Timeout or cancelled read replies force data_len = 0",
    "The DLL copy gate must prove data_len <= Length and data_len fits inside the received reply before copying",
]:
    require(contracts, term, "schema")

wire = (ROOT / "Sandboxie/core/svc/namedpipewire.h").read_text()
svc = (ROOT / "Sandboxie/core/svc/namedpipeserver.cpp").read_text()
dll = (ROOT / "Sandboxie/core/dll/file_pipe.c").read_text()
spec = (ROOT / "docs/plan/srev-151-namedpipe-read-reply-actual-length.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-151.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "struct tagNAMED_PIPE_READ_REQ",
    "ULONG read_len;",
    "struct tagNAMED_PIPE_READ_RPL",
    "NAMED_PIPE_IOSB iosb;",
    "ULONG data_len;",
    "UCHAR data[1];",
]:
    require(wire, term, "namedpipewire.h")

read_handler = between(
    svc,
    "MSG_HEADER *NamedPipeServer::ReadHandler(",
    "//---------------------------------------------------------------------------\n// WriteHandler",
)
for term in [
    "const ULONG rpl_len = FIELD_OFFSET(NAMED_PIPE_READ_RPL, data) + req->read_len;",
    "memzero(&IoStatusBlock, sizeof(IoStatusBlock));",
    "rpl->data_len = 0;",
    "rpl->data, req->read_len, &li, NULL);",
    "rpl->h.status = NamedPipeServer_WaitForPendingIo(",
    "if (IoStatusBlock.Information <= req->read_len)",
    "rpl->data_len = (ULONG)IoStatusBlock.Information;",
    "rpl->h.status = STATUS_INVALID_PARAMETER;",
    "IoStatusBlock.Status = STATUS_INVALID_PARAMETER;",
    "rpl->iosb.status = IoStatusBlock.Status;",
    "rpl->iosb.information = IoStatusBlock.Information;",
]:
    require(read_handler, term, "ReadHandler")
for term in [
    "IoStatusBlock->Status = STATUS_CANCELLED;",
    "IoStatusBlock->Information = 0;",
]:
    require(svc, term, "pending I/O cancel helper")
reject(read_handler, "rpl->data_len = req->read_len;", "stale read reply length")
if not (
    read_handler.index("rpl->data_len = 0;")
    < read_handler.index("NtReadFile(")
    < read_handler.index("if (IoStatusBlock.Information <= req->read_len)")
    < read_handler.index("rpl->data_len = (ULONG)IoStatusBlock.Information;")
    < read_handler.index("rpl->iosb.status = IoStatusBlock.Status;")
):
    raise SystemExit("SREV-151 failed: service data_len/order is wrong")

read_file = between(
    dll,
    "_FX NTSTATUS File_NtReadFile(",
    "//---------------------------------------------------------------------------\n// File_NtWriteFile",
)
for term in [
    "ULONG offset = FIELD_OFFSET(NAMED_PIPE_READ_RPL, data);",
    "if (rpl->h.length >= offset)",
    "IoStatusBlock->Status = (NTSTATUS)(ULONG_PTR)rpl->iosb.status;",
    "IoStatusBlock->Information = (ULONG_PTR)rpl->iosb.information;",
    "if (rpl->data_len > Length || rpl->data_len > rpl->h.length - offset)",
    "status = STATUS_INVALID_PARAMETER;",
    "IoStatusBlock->Information = 0;",
    "else if (rpl->data_len)",
    "memcpy(Buffer, rpl->data, rpl->data_len);",
    "else if (NT_SUCCESS(status))",
]:
    require(read_file, term, "File_NtReadFile")
reject(read_file, "if (rpl->h.length > sizeof(MSG_HEADER))", "stale reply header gate")
if not (
    read_file.index("ULONG offset = FIELD_OFFSET(NAMED_PIPE_READ_RPL, data);")
    < read_file.index("if (rpl->h.length >= offset)")
    < read_file.index("if (rpl->data_len > Length || rpl->data_len > rpl->h.length - offset)")
    < read_file.index("memcpy(Buffer, rpl->data, rpl->data_len);")
):
    raise SystemExit("SREV-151 failed: DLL copy gate/order is wrong")

for term in [
    "Sandboxie/core/svc/namedpipewire.h",
    "Sandboxie/core/svc/namedpipeserver.cpp",
    "Sandboxie/core/dll/file_pipe.c",
    "### SREV-151: Named Pipe Read Reply Actual Length",
    "NAMEDPIPE_READ_REPLY_ACTUAL_LENGTH",
    "srev-151-namedpipe-read-reply-actual-length.schema.json",
    "NtReadFile",
    "IO_STATUS_BLOCK",
    "actual transfer length",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-151 schema/source gate passed")
