#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-023 failed: {label} missing {needle!r}")


schema = json.loads((ROOT / "docs/plan/srev-023-pipeserver-thread-liveness.schema.json").read_text())
if schema.get("id") != "PIPESERVER_THREAD_LIVENESS_SHAPE":
    raise SystemExit("SREV-023 failed: schema missing PIPESERVER_THREAD_LIVENESS_SHAPE")

src = (ROOT / "Sandboxie/core/svc/PipeServer.cpp").read_text()
spec = (ROOT / "docs/plan/srev-023-pipeserver-thread-liveness.md").read_text()
ledger = read_combined_ledger(ROOT)

if "fix-me: when closing the port without waiting" in src:
    raise SystemExit("SREV-023 failed: stale cleanup fix-me remains")

for term in [
    "typedef DWORD (*P_GetProcessIdOfThread)(HANDLE Thread);",
    "THREAD_QUERY_INFORMATION | SYNCHRONIZE",
    "DWORD WaitStatus = WaitForSingleObject(hThread, 0);",
    "WaitStatus == WAIT_TIMEOUT",
]:
    require(src, term, "service source")

for term in [
    "https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-getprocessidofthread",
    "https://learn.microsoft.com/en-us/windows/win32/api/synchapi/nf-synchapi-waitforsingleobject",
    "thread object's state becomes",
]:
    require(spec, term, "spec")

for term in [
    "### SREV-023: Legacy LPC Disconnect Treats Dead Thread Object As Live",
    "WAIT_TIMEOUT",
    "PortDisconnectByCreateTime",
]:
    require(ledger, term, "ledger")

print("SREV-023 schema/source gate passed")
