#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-074 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-074 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-074-api-current-process-sentinel.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-074 failed: schema is not draft-07")
if schema.get("id") != "API_CURRENT_PROCESS_SENTINEL_WIDTH":
    raise SystemExit("SREV-074 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "API arguments are captured into ULONG64 slots",
    "special HANDLE sentinel values for the current process",
    "pointer-precision types rather than ULONG truncation",
    "native pointer-width -1 sentinel",
    "zero-extended 32-bit 0xffffffff WOW64 sentinel",
    "reject arbitrary 64-bit values that only match after truncation to ULONG",
]:
    require(contracts, term, "schema")

api_h = (ROOT / "Sandboxie/core/drv/api.h").read_text()
driver_h = (ROOT / "Sandboxie/core/drv/driver.h").read_text()
ipc_c = (ROOT / "Sandboxie/core/drv/ipc.c").read_text()
process_api_c = (ROOT / "Sandboxie/core/drv/process_api.c").read_text()
file_c = (ROOT / "Sandboxie/core/drv/file.c").read_text()
spec = (ROOT / "docs/plan/srev-074-api-current-process-sentinel.md").read_text()
ledger = read_combined_ledger(ROOT)

for term in [
    "SREV-074: shared warning suppressions cover legacy pointer/HANDLE casts.",
    "Driver API current-process sentinels must use api.h's width-exact predicate.",
    "warning C4311",
    "warning C4312",
]:
    require(driver_h, term, "driver.h sentinel-width comment")

reject(driver_h, "HACK ALERT we must fix this 32 vs. 64 bit handle problem", "driver.h hack comment")

for term in [
    "API_ARGS are 64-bit slots",
    "WOW64 callers can pass the 32-bit",
    "#define IS_ARG_CURRENT_PROCESS(h) \\",
    "(((ULONG_PTR)(h) == (ULONG_PTR)-1) || ((ULONG_PTR)(h) == (ULONG_PTR)0xffffffff))",
]:
    require(api_h, term, "api.h macro")

if "((ULONG)h == 0xffffffff)" in api_h:
    raise SystemExit("SREV-074 failed: stale ULONG truncating sentinel predicate remains")

if api_h.index("(ULONG_PTR)(h) == (ULONG_PTR)-1") > api_h.index("(ULONG_PTR)(h) == (ULONG_PTR)0xffffffff"):
    raise SystemExit("SREV-074 failed: native sentinel check should appear before WOW64 sentinel")

callsite_count = (
    ipc_c.count("IS_ARG_CURRENT_PROCESS(")
    + process_api_c.count("IS_ARG_CURRENT_PROCESS(")
    + file_c.count("IS_ARG_CURRENT_PROCESS(")
)
if callsite_count < 13:
    raise SystemExit(f"SREV-074 failed: expected current call sites, found {callsite_count}")

for term in [
    "https://learn.microsoft.com/en-us/windows/win32/winprog64/rules-for-using-pointers",
    "https://learn.microsoft.com/en-us/windows/win32/winprog64/the-new-data-types",
    "https://learn.microsoft.com/en-us/windows-hardware/drivers/kernel/zwcurrentprocess",
    "srev-074-api-current-process-sentinel.schema.json",
]:
    require(spec, term, "spec")

for term in [
    "### SREV-074: API Current Process Sentinel Width",
    "API_CURRENT_PROCESS_SENTINEL_WIDTH",
    "Sandboxie/core/drv/driver.h",
    "srev-074-api-current-process-sentinel.schema.json",
]:
    require(ledger, term, "ledger")

print("SREV-074 schema/source gate passed")
