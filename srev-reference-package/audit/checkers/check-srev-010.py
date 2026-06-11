#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-010 failed: {label} missing {needle!r}")


schema = json.loads((ROOT / "docs/plan/srev-010-uac-helper-wait.schema.json").read_text())
if schema.get("id") != "UAC_HELPER_WAIT_BOUNDARY":
    raise SystemExit("SREV-010 failed: schema missing UAC_HELPER_WAIT_BOUNDARY")

src = (ROOT / "Sandboxie/core/svc/serviceserver2.cpp").read_text()
spec = (ROOT / "docs/plan/srev-010-uac-helper-wait.md").read_text()
ledger = read_combined_ledger(ROOT)

for term in [
    "SBIE_UAC_PROMPT_TIMEOUT_MS",
    "WaitForSingleObject(",
    "WaitStatus == WAIT_OBJECT_0",
    "WaitStatus == WAIT_TIMEOUT",
    "TerminateProcess(pi.hProcess, ERROR_TIMEOUT)",
    "SetLastError(ERROR_TIMEOUT)",
]:
    require(src, term, "service source")

prompt = src.find("uac_prompt %08X_%08X_%08X_%08X")
wait = src.find("WaitForSingleObject(", prompt)
timeout = src.find("SBIE_UAC_PROMPT_TIMEOUT_MS", wait)
fail = src.find("ok = FALSE;", timeout)
just_fail = src.find("RunUacSlave3(idProcess, pkt_addr, pkt_len, true, NULL)", fail)
if min(prompt, wait, timeout, fail, just_fail) < 0:
    raise SystemExit("SREV-010 failed: prompt timeout/fail-closed path incomplete")
if "WaitForSingleObject(pi.hProcess, INFINITE)" in src[prompt:just_fail]:
    raise SystemExit("SREV-010 failed: uac_prompt helper still waits forever")
if not (wait < timeout < fail < just_fail):
    raise SystemExit("SREV-010 failed: timeout must lead to existing JustFail path")

for term in ["WaitForSingleObject", "WAIT_TIMEOUT", "TerminateProcess"]:
    require(spec, term, "spec")

require(ledger, "### SREV-010: Sandboxie UAC Broker Waits Forever On Helper Process", "ledger")
require(ledger, "Sandboxie/core/svc/serviceserver2.cpp", "ledger")

print("SREV-010 schema/source gate passed")
