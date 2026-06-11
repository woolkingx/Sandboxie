#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-222 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-222 failed: {label} still contains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-222-user-proxy-wire-buffer-bounds.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-222 failed: schema is not draft-07")
if schema.get("id") != "USER_PROXY_WIRE_BUFFER_BOUNDS":
    raise SystemExit("SREV-222 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "Queue request data is caller-controlled wire data",
    "QueueCallbackWorker2 may read a msgid only after data_len is at least sizeof(ULONG)",
    "USER_OPEN_FILE_REQ FileNameOffset must point inside the received request buffer",
    "USER_SHELL_EXEC_REQ FileNameOffset must point inside the received request buffer",
    "USER_OPEN_FILE_REQ EaBufferOffset is optional",
    "File_NtCreateFileProxy copies exactly ObjectName Length bytes",
]:
    require(contracts, term, "schema")

spec = (ROOT / "docs/plan/srev-222-user-proxy-wire-buffer-bounds.md").read_text()
ledger = read_combined_ledger(ROOT)
user_server = (ROOT / "Sandboxie/core/svc/UserServer.cpp").read_text()
file_c = (ROOT / "Sandboxie/core/dll/file.c").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

queue_callback = user_server[
    user_server.index("bool UserServer::QueueCallbackWorker2"):
    user_server.index("// send reply")
]
for term in [
    "if (data_len < sizeof(ULONG))",
    "status = STATUS_INFO_LENGTH_MISMATCH;",
    "else {",
    "ULONG msgid = *(ULONG *)data_ptr;",
]:
    require(queue_callback, term, "QueueCallbackWorker2 short msgid gate")

short_gate_pos = queue_callback.index("if (data_len < sizeof(ULONG))")
msgid_pos = queue_callback.index("ULONG msgid = *(ULONG *)data_ptr;")
if short_gate_pos > msgid_pos:
    raise SystemExit("SREV-222 failed: msgid read appears before short-data gate")

for term in [
    "static WCHAR *UserServer_GetWireString(",
    "if (offset < min_offset || offset > req_len)",
    "if ((offset & (sizeof(WCHAR) - 1)) != 0)",
    "ULONG bytes_left = req_len - offset;",
    "if (string[index] == L'\\0')",
    "static void *UserServer_GetWireRange(",
    "if (length > req_len - offset)",
]:
    require(user_server, term, "UserServer wire helper")

open_file = user_server[
    user_server.index("ULONG UserServer::OpenFile"):
    user_server.index("ULONG UserServer::OpenDocument")
]
for term in [
    "UserServer_GetWireString(\n        req, args->req_len, req->FileNameOffset, sizeof(USER_OPEN_FILE_REQ))",
    "if (! path_buff)\n        return STATUS_INFO_LENGTH_MISMATCH;",
    "UserServer_GetWireRange(\n            req, args->req_len, req->EaBufferOffset, req->EaLength,",
    "if (! pEaBuff)\n            return STATUS_INFO_LENGTH_MISMATCH;",
    "RtlInitUnicodeString(&objname, path_buff);",
    "NtCreateFile(&hFile",
]:
    require(open_file, term, "OpenFile bounded wire use")

open_document = user_server[
    user_server.index("ULONG UserServer::OpenDocument"):
    user_server.index("// GetProcessPathList")
]
for term in [
    "UserServer_GetWireString(\n        req, args->req_len, req->FileNameOffset, sizeof(USER_SHELL_EXEC_REQ))",
    "if (! path_buff)\n        return STATUS_INFO_LENGTH_MISMATCH;",
    "shex.lpFile = path_buff;",
]:
    require(open_document, term, "OpenDocument bounded wire use")

proxy_start = file_c.index("\nNTSTATUS File_NtCreateFileProxy")
proxy = file_c[
    proxy_start:
    file_c.index("//---------------------------------------------------------------------------", proxy_start + 1)
]
for term in [
    "ObjectAttributes->ObjectName->Buffer == NULL",
    "ULONG name_len = ObjectAttributes->ObjectName->Length;",
    "if ((name_len & (sizeof(WCHAR) - 1)) != 0)",
    "name_len > (ULONG)-1 - sizeof(USER_OPEN_FILE_REQ) - sizeof(WCHAR)",
    "EaLength > (ULONG)-1 - sizeof(USER_OPEN_FILE_REQ) - sizeof(WCHAR) - name_len",
    "ULONG path_len = name_len + sizeof(WCHAR);",
    "memcpy(path_buff, ObjectAttributes->ObjectName->Buffer, name_len);",
    "path_buff[name_len / sizeof(WCHAR)] = L'\\0';",
]:
    require(proxy, term, "File_NtCreateFileProxy counted string producer")
reject(proxy, "memcpy(path_buff, ObjectAttributes->ObjectName->Buffer, path_len);", "old counted-string overread")

for term in [
    "### SREV-222: User Proxy Wire Buffer Bounds",
    "USER_PROXY_WIRE_BUFFER_BOUNDS",
    "srev-222-user-proxy-wire-buffer-bounds.schema.json",
    "Sandboxie/core/svc/UserServer.cpp",
    "Sandboxie/core/svc/UserWire.h",
    "Sandboxie/core/dll/file.c",
    "QueueCallbackWorker2",
    "File_NtCreateFileProxy",
    "STATUS_INFO_LENGTH_MISMATCH",
]:
    require(ledger, term, "ledger")

print("SREV-222 source gate passed")
