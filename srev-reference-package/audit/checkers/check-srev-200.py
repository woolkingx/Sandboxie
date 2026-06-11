#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-200 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-200 failed: stale {label} remains {needle!r}")


def between(text: str, start: str, end: str) -> str:
    a = text.index(start)
    b = text.index(end, a + len(start))
    return text[a:b]


schema = json.loads(
    (ROOT / "docs/plan/srev-200-file-server-openboxfile-path-gate.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-200 failed: schema is not draft-07")
if schema.get("id") != "FILE_SERVER_OPENBOXFILE_PATH_GATE":
    raise SystemExit("SREV-200 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/svc/fileserver.h":
    raise SystemExit("SREV-200 failed: wrong owner")
if schema.get("implementation") != "Sandboxie/core/svc/fileserver.cpp":
    raise SystemExit("SREV-200 failed: wrong implementation")

contracts = "\n".join(schema["contracts"])
for term in [
    "OpenBoxFile returns NTSTATUS and must not call SHORT_REPLY",
    "CheckBoxFilePath failure returns status before RtlInitUnicodeString",
    "NtCreateFile is reachable only after sandbox path gate success",
]:
    require(contracts, term, "schema contract")

src = (ROOT / "Sandboxie/core/svc/fileserver.cpp").read_text()
header = (ROOT / "Sandboxie/core/svc/fileserver.h").read_text()
spec = (ROOT / "docs/plan/srev-200-file-server-openboxfile-path-gate.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-200.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "NTSTATUS OpenBoxFile(",
    "HANDLE idProcess, WCHAR *request_path,",
    "ACCESS_MASK desired_access, ULONG create_options,",
]:
    require(header, term, "header owner declaration")

openbox = between(
    src,
    "NTSTATUS FileServer::OpenBoxFile(",
    "//---------------------------------------------------------------------------\n// LoadKey",
)
for term in [
    "NTSTATUS status = CheckBoxFilePath(idProcess, request_path, L\"\\\\\");",
    "if (! NT_SUCCESS(status))",
    "return status;",
    "RtlInitUnicodeString(&objname, request_path);",
    "InitializeObjectAttributes(",
    "status = NtCreateFile(",
]:
    require(openbox, term, "OpenBoxFile path gate")

reject(openbox, "SHORT_REPLY(status);", "OpenBoxFile SHORT_REPLY misuse")
if not openbox.index("CheckBoxFilePath") < openbox.index("RtlInitUnicodeString(&objname, request_path);"):
    raise SystemExit("SREV-200 failed: path gate is after RtlInitUnicodeString")
if not openbox.index("return status;") < openbox.index("RtlInitUnicodeString(&objname, request_path);"):
    raise SystemExit("SREV-200 failed: failure return is after object-name setup")
if not openbox.index("return status;") < openbox.index("status = NtCreateFile("):
    raise SystemExit("SREV-200 failed: failure return is after NtCreateFile")

set_attributes = between(
    src,
    "MSG_HEADER *FileServer::SetAttributes(",
    "//---------------------------------------------------------------------------\n// SetShortName",
)
for term in [
    "status = OpenBoxFile(",
    "return SHORT_REPLY(status);",
]:
    require(set_attributes, term, "SetAttributes handler boundary")

set_short_name = between(
    src,
    "MSG_HEADER *FileServer::SetShortName(",
    "//---------------------------------------------------------------------------\n// OpenBoxFile",
)
for term in [
    "status = OpenBoxFile(",
    "return SHORT_REPLY(status);",
]:
    require(set_short_name, term, "SetShortName handler boundary")

for term in [
    "kind: srev-ledger-entry",
    "id: SREV-200",
    "owner: Sandboxie/core/svc/fileserver.h",
    "implementation: Sandboxie/core/svc/fileserver.cpp",
    "spec: docs/plan/srev-200-file-server-openboxfile-path-gate.md",
    "schema: docs/plan/srev-200-file-server-openboxfile-path-gate.schema.json",
    "checker: docs/plan/check-srev-200.py",
    "patched source-level after official NtCreateFile shape review",
]:
    require(ledger_fragment, term, "ledger fragment")
    require(ledger, term, "combined ledger")

print("SREV-200 source gate passed")
