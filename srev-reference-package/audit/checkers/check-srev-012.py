#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-012 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-012 failed: {label} still contains {needle!r}")


schema = json.loads((ROOT / "docs/plan/srev-012-reparse-buffer-spec.schema.json").read_text())
if schema.get("id") != "REPARSE_BUFFER_SHAPE":
    raise SystemExit("SREV-012 failed: schema missing REPARSE_BUFFER_SHAPE")

src = (ROOT / "Sandboxie/core/dll/file_dir.c").read_text()
spec = (ROOT / "docs/plan/srev-012-reparse-buffer-spec.md").read_text()
ledger = read_combined_ledger(ROOT)

for term in [
    "File_CheckReparseNameRange",
    "ReparseDataLength > DataLen - ReparseHeaderLength",
    "PathBufferRelativeOffset > ReparseDataLength",
    "NameLength > PathBufferLength - NameOffset",
    "DataLen < PathBufferOffset",
    "memcpy(PrintNameBuffer, OldPrintNameBuffer, PrintNameLength)",
    "PrintNameBuffer[PrintNameLength / sizeof(WCHAR)] = L'\\0'",
    "MAXIMUM_REPARSE_DATA_BUFFER_SIZE",
    "status = STATUS_INVALID_PARAMETER",
]:
    require(src, term, "DLL source")

reject(src, "memcpy(PrintNameBuffer, OldPrintNameBuffer, PrintNameLength + sizeof(WCHAR))", "DLL source")

require(spec, "FsRtlValidateReparsePointBuffer", "spec")

require(ledger, "### SREV-012: Reparse Point Buffer Parser Trusts Embedded Offsets And Lengths", "ledger")
require(ledger, "Sandboxie/core/dll/file_dir.c", "ledger")

print("SREV-012 schema/source gate passed")
