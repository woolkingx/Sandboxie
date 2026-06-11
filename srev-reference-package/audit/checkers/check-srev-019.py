#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-019 failed: {label} missing {needle!r}")


schema = json.loads((ROOT / "docs/plan/srev-019-rename-link-length-spec.schema.json").read_text())
if schema.get("id") != "RENAME_LINK_LENGTH_SHAPE":
    raise SystemExit("SREV-019 failed: schema missing RENAME_LINK_LENGTH_SHAPE")

src = (ROOT / "Sandboxie/core/drv/file_flt.c").read_text()
spec = (ROOT / "docs/plan/srev-019-rename-link-length-spec.md").read_text()
ledger = read_combined_ledger(ROOT)

for term in [
    "File_CheckRenameLinkNameLength",
    "FileNameLength > MAXUSHORT",
    "FileNameLength & (sizeof(WCHAR) - 1)",
    "BufferLength < FileNameOffset",
    "FileNameLength > BufferLength - FileNameOffset",
    "SetFileInformation.Length",
    "FIELD_OFFSET(FILE_LINK_INFORMATION, FileName)",
    "FIELD_OFFSET(FILE_RENAME_INFORMATION, FileName)",
]:
    require(src, term, "driver source")

for name in ("infoL", "infoR"):
    gate = src.find(f"{name}->FileNameLength))")
    cast = src.find(f"FileName.Length = (USHORT){name}->FileNameLength;")
    if gate < 0 or cast < 0:
        raise SystemExit(f"SREV-019 failed: missing gate or cast for {name}")
    if not gate < cast:
        raise SystemExit(f"SREV-019 failed: {name} length cast precedes gate")

for term in ["FILE_RENAME_INFORMATION", "FILE_LINK_INFORMATION", "SetFileInformation.Length", "MAXUSHORT"]:
    require(spec, term, "spec")

require(ledger, "### SREV-019: Rename/Link Target Length Is Truncated From ULONG To USHORT Before Policy Parse", "ledger")
require(ledger, "Sandboxie/core/drv/file_flt.c", "ledger")

print("SREV-019 schema/source gate passed")
