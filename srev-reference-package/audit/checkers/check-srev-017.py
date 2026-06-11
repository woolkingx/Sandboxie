#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-017 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-017 failed: {label} still contains {needle!r}")


schema = json.loads((ROOT / "docs/plan/srev-017-breakout-command-line-spec.schema.json").read_text())
if schema.get("id") != "BREAKOUT_COMMAND_LINE_SHAPE":
    raise SystemExit("SREV-017 failed: schema missing BREAKOUT_COMMAND_LINE_SHAPE")

src = (ROOT / "Sandboxie/core/dll/proc.c").read_text()
spec = (ROOT / "docs/plan/srev-017-breakout-command-line-spec.md").read_text()
ledger = read_combined_ledger(ROOT)

reject(src, "wcscpy(temp, tmp)", "DLL source")
reject(src, "temp[len - 2]", "DLL source")

for term in [
    "ULONG tmp_len = len",
    "tmp_len >= 2",
    "tmp_len < 8192",
    "wmemcpy(temp, tmp, tmp_len)",
    "temp[tmp_len] = L'\\0'",
    "wcscat(mybuf, lpArguments)",
]:
    require(src, term, "DLL source")

for term in ["CreateProcessW", "32,767", "CommandLineToArgvW"]:
    require(spec, term, "spec")

require(ledger, "### SREV-017: Breakout Command-Line Argument Copy Can Overflow Fixed Buffer", "ledger")
require(ledger, "Sandboxie/core/dll/proc.c", "ledger")

print("SREV-017 schema/source gate passed")
