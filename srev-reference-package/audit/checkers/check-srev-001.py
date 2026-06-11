#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-001 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-001 failed: {label} still contains {needle!r}")


schema = json.loads((ROOT / "docs/plan/srev-001-directory-info-spec.schema.json").read_text())
if schema.get("id") != "DIRECTORY_INFO_BUFFER_SHAPE":
    raise SystemExit("SREV-001 failed: schema missing DIRECTORY_INFO_BUFFER_SHAPE")

contracts = "\n".join(schema["contracts"])
for term in [
    "FILE_ID_BOTH_DIR_INFORMATION is a variable-size record",
    "FileNameLength is a length in bytes",
    "8-byte boundary",
    "File_MergeDummy must check remaining info_area capacity",
    "File_MergeDummy must treat FileNameLength as a byte count",
]:
    require(contracts, term, "schema contracts")

src = (ROOT / "Sandboxie/core/dll/file_dir.c").read_text()
spec = (ROOT / "docs/plan/srev-001-directory-info-spec.md").read_text()
ledger = read_combined_ledger(ROOT)

for term in [
    "FIELD_OFFSET(FILE_ID_BOTH_DIR_INFORMATION, FileName)",
    "entry_len > INFO_AREA_LEN - used",
]:
    require(src, term, "DLL source")

reject(src, "FileName[info_ptr->FileNameLength]", "DLL source")

for term in [
    "FileNameLength",
    "bytes",
]:
    require(spec, term, "spec")

for term in [
    "### SREV-001: Dummy Directory Merge Uses Unbounded Fixed Buffer",
    "Sandboxie/core/dll/file_dir.c",
]:
    require(ledger, term, "ledger")

print("SREV-001 schema/source gate passed")
