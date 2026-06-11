#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-021 failed: {label} missing {needle!r}")


schema = json.loads((ROOT / "docs/plan/srev-021-uac-thread-handle-ownership.schema.json").read_text())
if schema.get("id") != "UAC_SLAVE_THREAD_HANDLE_OWNERSHIP":
    raise SystemExit("SREV-021 failed: schema missing UAC_SLAVE_THREAD_HANDLE_OWNERSHIP")

src = (ROOT / "Sandboxie/core/svc/serviceserver2.cpp").read_text()
spec = (ROOT / "docs/plan/srev-021-uac-thread-handle-ownership.md").read_text()
ledger = read_combined_ledger(ROOT)

if "fix-me: i'm leaking a thread" in src:
    raise SystemExit("SREV-021 failed: leaked-thread fix-me remains in source")

for term in [
    "CreateThread",
    "CloseHandle",
    "https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-createthread",
    "https://learn.microsoft.com/en-us/windows/win32/api/handleapi/nf-handleapi-closehandle",
]:
    require(spec, term, "spec")

expected = {
    "HANDLE hThread1 = CreateThread(": 2,
    "HANDLE hThread2 = CreateThread(": 2,
    "CloseHandle(hThread1);": 2,
    "CloseHandle(hThread2);": 2,
}
for needle, want in expected.items():
    got = src.count(needle)
    if got != want:
        raise SystemExit(f"SREV-021 failed: expected {want} occurrences of {needle!r}, got {got}")

if src.index("HANDLE hThread1 = CreateThread(") > src.index("CloseHandle(hThread1);"):
    raise SystemExit("SREV-021 failed: hThread1 close precedes creation")
if src.index("HANDLE hThread2 = CreateThread(") > src.index("CloseHandle(hThread2);"):
    raise SystemExit("SREV-021 failed: hThread2 close precedes creation")

require(ledger, "### SREV-021: UAC Slave Thread Handles Are Not Closed", "ledger")
require(ledger, "Sandboxie/core/svc/serviceserver2.cpp", "ledger")

print("SREV-021 schema/source gate passed")
