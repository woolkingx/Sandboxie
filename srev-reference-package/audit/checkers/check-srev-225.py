#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-225 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-225 failed: {label} still contains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-225-interactive-file-migration-path-bounds.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-225 failed: schema is not draft-07")
if schema.get("id") != "INTERACTIVE_FILE_MIGRATION_PATH_BOUNDS":
    raise SystemExit("SREV-225 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "MAN_FILE_MIGRATION_REQ file_path as a fixed 256 WCHAR interactive queue field",
    "serializes TruePath into the fixed field before crossing the MANPROXY queue boundary",
    "must not use an unbounded string copy into file_path[256]",
    "must zero the full request before sending it",
    "must always NUL terminate file_path inside the fixed field",
]:
    require(contracts, term, "schema")

spec = (ROOT / "docs/plan/srev-225-interactive-file-migration-path-bounds.md").read_text()
ledger = read_combined_ledger(ROOT)
wire_h = (ROOT / "Sandboxie/core/svc/InteractiveWire.h").read_text()
file_copy = (ROOT / "Sandboxie/core/dll/file_copy.c").read_text()
sbie_api = (ROOT / "SandboxiePlus/QSbieAPI/SbieAPI.cpp").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "#define INTERACTIVE_QUEUE_NAME L\"MANPROXY\"",
    "#define MAN_FILE_MIGRATION 1",
    "ULONGLONG file_size;",
    "WCHAR file_path[256];",
]:
    require(wire_h, term, "InteractiveWire wire shape")

producer = file_copy[
    file_copy.index("_FX ULONG File_MigrateFile_GetMode"):
    file_copy.index("// File_InitCopyLimit", file_copy.index("_FX ULONG File_MigrateFile_GetMode"))
]
for term in [
    "MAN_FILE_MIGRATION_REQ req;",
    "memzero(&req, sizeof(req));",
    "req.msgid = MAN_FILE_MIGRATION;",
    "req.file_size = file_size;",
    "ULONG path_chars = wcslen(TruePath);",
    "if (path_chars >= ARRAYSIZE(req.file_path))",
    "path_chars = ARRAYSIZE(req.file_path) - 1;",
    "wmemcpy(req.file_path, TruePath, path_chars);",
    "req.file_path[path_chars] = L'\\0';",
    "SbieDll_CallServerQueue(INTERACTIVE_QUEUE_NAME, &req, sizeof(req), sizeof(*rpl))",
]:
    require(producer, term, "file_copy producer source shape")
reject(producer, "wcscpy(req.file_path, TruePath);", "old unbounded file_path copy")

consumer = sbie_api[
    sbie_api.index("bool CSbieAPI::GetQueueReq"):
    sbie_api.index("void CSbieAPI::SendQueueRpl")
]
for term in [
    "case MAN_FILE_MIGRATION:",
    "MAN_FILE_MIGRATION_REQ *req = (MAN_FILE_MIGRATION_REQ *)rpl->data;",
    "Data[\"fileSize\"] = req->file_size;",
    "QString::fromWCharArray(req->file_path)",
]:
    require(consumer, term, "Qt consumer topology")

for term in [
    "### SREV-225: Interactive File Migration Path Bounds",
    "INTERACTIVE_FILE_MIGRATION_PATH_BOUNDS",
    "srev-225-interactive-file-migration-path-bounds.schema.json",
    "Sandboxie/core/svc/InteractiveWire.h",
    "Sandboxie/core/dll/file_copy.c",
    "SandboxiePlus/QSbieAPI/SbieAPI.cpp",
    "file_path[256]",
    "memzero(&req, sizeof(req));",
]:
    require(ledger, term, "ledger")

print("SREV-225 source gate passed")
