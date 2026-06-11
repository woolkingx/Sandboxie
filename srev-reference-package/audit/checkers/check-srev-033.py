#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-033 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-033 failed: {label} still contains {needle!r}")


schema = json.loads((ROOT / "docs/plan/srev-033-file-key-exists-wire.schema.json").read_text())
if schema.get("id") != "FILE_CHECK_KEY_EXISTS_WIRE_STRING":
    raise SystemExit("SREV-033 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "KeyPath_len is a byte count, not a WCHAR count",
    "KeyPath_len must be aligned to sizeof(WCHAR)",
    "KeyPath[KeyPath_len / sizeof(WCHAR) - 1] must be NUL",
    "RtlInitUnicodeString receives only a bounded NUL-terminated WCHAR string",
]:
    require(contracts, term, "schema")

svc = (ROOT / "Sandboxie/core/svc/fileserver.cpp").read_text()
sender = (ROOT / "Sandboxie/core/dll/key_merge.c").read_text()
spec = (ROOT / "docs/plan/srev-033-file-key-exists-wire.md").read_text()
ledger = read_combined_ledger(ROOT)

for term in [
    "static BOOLEAN FileServer_IsValidWireWString(",
    "if ((! byte_len) || (byte_len > PIPE_MAX_DATA_LEN))",
    "if (byte_len & (sizeof(WCHAR) - 1))",
    "if (offset > msg_len || byte_len > msg_len - offset)",
    "return text[byte_len / sizeof(WCHAR) - 1] == L'\\0';",
]:
    require(svc, term, "service helper")

check_start = svc.index("MSG_HEADER *FileServer::CheckKeyExists")
check_end = svc.index("// CheckBoxFilePath", check_start)
check = svc[check_start:check_end]
for term in [
    "FILE_CHECK_KEY_EXISTS_REQ *req",
    "FIELD_OFFSET(FILE_CHECK_KEY_EXISTS_REQ, KeyPath)",
    "FileServer_IsValidWireWString(",
    "req->h.length, offset, req->KeyPath_len, req->KeyPath",
    "CheckBoxKeyPath(idProcess, req->KeyPath, L\"\\\\\")",
    "RtlInitUnicodeString(&objname, req->KeyPath);",
]:
    require(check, term, "CheckKeyExists")

reject(check, "offset + req->KeyPath_len > req->h.length", "CheckKeyExists")
require(sender, "req->KeyPath_len = path_len * sizeof(WCHAR);", "sender")
reject(sender, "req->KeyPath_len = path_len;\n", "sender")

for term in [
    "https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-rtlinitunicodestring",
    "https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-zwopenkey",
    "srev-033-file-key-exists-wire.schema.json",
]:
    require(spec, term, "spec")

for term in [
    "### SREV-033: File Check Key Exists Wire String",
    "FileServer_IsValidWireWString",
    "srev-033-file-key-exists-wire.schema.json",
]:
    require(ledger, term, "ledger")

print("SREV-033 schema/source gate passed")
