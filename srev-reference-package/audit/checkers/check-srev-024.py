#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-024 failed: {label} missing {needle!r}")


schema = json.loads((ROOT / "docs/plan/srev-024-killall-enum-count.schema.json").read_text())
if schema.get("id") != "KILLALL_ENUM_COUNT_SHAPE":
    raise SystemExit("SREV-024 failed: schema missing KILLALL_ENUM_COUNT_SHAPE")

src = (ROOT / "Sandboxie/core/svc/ProcessServer.cpp").read_text()
spec = (ROOT / "docs/plan/srev-024-killall-enum-count.md").read_text()
ledger = read_combined_ledger(ROOT)

for term in ["BOOLEAN TerminateJob = FALSE;", "for (i = 0; i < count; ++i)"]:
    require(src, term, "service source")
if "for (i = 0; i <= count; ++i)" in src:
    raise SystemExit("SREV-024 failed: off-by-one PID loop remains")

for term in [
    "https://learn.microsoft.com/en-us/windows/win32/api/jobapi2/nf-jobapi2-terminatejobobject",
    "https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-terminateprocess",
    "0 <= i < count",
]:
    require(spec, term, "spec")

for term in [
    "### SREV-024: KillAll Uses Uninitialized Job Mode And Reads Past PID Count",
    "TerminateJob = FALSE",
    "pids[count]",
]:
    require(ledger, term, "ledger")

print("SREV-024 schema/source gate passed")
