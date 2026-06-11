#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-014 failed: {label} missing {needle!r}")


schema = json.loads((ROOT / "docs/plan/srev-014-fsctl-pipe-wait-spec.schema.json").read_text())
if schema.get("id") != "FSCTL_PIPE_WAIT_BUFFER_SHAPE":
    raise SystemExit("SREV-014 failed: schema missing FSCTL_PIPE_WAIT_BUFFER_SHAPE")

src = (ROOT / "Sandboxie/core/dll/file_pipe.c").read_text()
spec = (ROOT / "docs/plan/srev-014-fsctl-pipe-wait-spec.md").read_text()
ledger = read_combined_ledger(ROOT)

for term in [
    "FIELD_OFFSET(FILE_PIPE_WAIT_FOR_BUFFER, Name)",
    "InputBufferLength < name_offset",
    "ib->NameLength & (sizeof(WCHAR) - 1)",
    "ib->NameLength > InputBufferLength - name_offset",
    "if (! ob)",
    "STATUS_INSUFFICIENT_RESOURCES",
]:
    require(src, term, "DLL source")

lines = src.splitlines()
first_name_read = next((i for i, l in enumerate(lines, 1) if "ib->NameLength" in l), -1)
fixed_gate = next((i for i, l in enumerate(lines, 1) if "InputBufferLength < name_offset" in l), -1)
if min(first_name_read, fixed_gate) < 0 or fixed_gate > first_name_read:
    raise SystemExit("SREV-014 failed: NameLength read precedes fixed header gate")

for term in ["FSCTL_PIPE_WAIT", "NameLength"]:
    require(spec, term, "spec")

require(ledger, "### SREV-014: FSCTL_PIPE_WAIT Parser Reads NameLength Before Input Buffer Shape Check", "ledger")
require(ledger, "Sandboxie/core/dll/file_pipe.c", "ledger")

print("SREV-014 schema/source gate passed")
