#!/usr/bin/env python3
import json
import re
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-013 failed: {label} missing {needle!r}")


schema = json.loads((ROOT / "docs/plan/srev-013-relative-symlink-canonicalizer.schema.json").read_text())
if schema.get("id") != "RELATIVE_SYMLINK_CANONICALIZER_SHAPE":
    raise SystemExit("SREV-013 failed: schema missing RELATIVE_SYMLINK_CANONICALIZER_SHAPE")

src = (ROOT / "Sandboxie/core/dll/file_dir.c").read_text()
spec = (ROOT / "docs/plan/srev-013-relative-symlink-canonicalizer.md").read_text()
ledger = read_combined_ledger(ROOT)

for term in [
    "ULONG root_floor = 0",
    "i + 1 < rel_path_len",
    "i + 2 == rel_path_len",
    "i < rel_path_len && relative_path[i] == L'\\\\'",
    "abs_path_len <= root_floor",
    "Dll_Free(result)",
    "if (! AbsolutePath)",
    "STATUS_INVALID_PARAMETER",
]:
    require(src, term, "DLL source")

if re.search(r"\bj\s*>=\s*0\b", src):
    raise SystemExit("SREV-013 failed: unsigned j >= 0 check remains")

require(spec, "symbolic-link reparse data buffer", "spec")

require(ledger, "### SREV-013: Relative Path Canonicalizer Uses Unsigned Index For Parent Traversal", "ledger")
require(ledger, "Sandboxie/core/dll/file_dir.c", "ledger")

print("SREV-013 schema/source gate passed")
