#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-066 failed: {label} missing {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-066-lowlevel-hotpatch-scan-window.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-066 failed: schema is not draft-07")
if schema.get("id") != "LOWLEVEL_HOTPATCH_SCAN_WINDOW":
    raise SystemExit("SREV-066 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "ReadProcessMemory copies nSize bytes",
    "scan_offset plus sizeof(ULONG_PTR) fits inside myBuffer",
    "Scan offsets are byte offsets",
    "must not use short-element indexing",
    "fail closed when no full ULONG_PTR pattern window is found",
    "Fallback comments must name SREV-066 instead of generic hack wording",
]:
    require(contracts, term, "schema")

src = (ROOT / "Sandboxie/core/dll/lowlevel_inject.c").read_text()
spec = (ROOT / "docs/plan/srev-066-lowlevel-hotpatch-scan-window.md").read_text()
ledger = read_combined_ledger(ROOT)

start = src.index("_FX void * SbieDll_InjectLow_getPage(")
end = src.index("#endif  //#ifdef _WIN64", start)
func = src[start:end]

for term in [
    "SREV-066: disable fallback scan attempts if nearby allocation fails.",
    "SREV-066: fallback scan for an 8-byte hotpatch slot.",
    "Scan the ntdll .rdata fallback window through byte offsets.",
    "ReadProcessMemory(hProcess, (void *)((ULONG_PTR)tempAddr + 0x100000), myBuffer, sizeof(myBuffer), &readSize);",
    "if (readSize != sizeof(myBuffer))",
    "for (SIZE_T i = 0; i + sizeof(ULONG_PTR) <= sizeof(myBuffer) && !myTable; i++)",
    "*((ULONG_PTR*)((UCHAR *)myBuffer + i)) == 0x9090909090909090",
    "*((ULONG_PTR*)((UCHAR *)myBuffer + i)) == 0xcccccccccccccccc",
    "myTable = (void *)((ULONG_PTR)tempAddr + i);",
]:
    require(func, term, "SbieDll_InjectLow_getPage source")

for stale in [
    "for (int i = 0; i < sizeof(myBuffer) && !myTable; i++)",
    "*((ULONG_PTR*)&myBuffer[i])",
    "use hack if all else fails",
    "not hot patch area: This is a hack",
    "HACK: table found",
]:
    if stale in func:
        raise SystemExit(f"SREV-066 failed: stale scan shape remains: {stale}")

for term in [
    "https://learn.microsoft.com/en-us/windows/win32/api/memoryapi/nf-memoryapi-readprocessmemory",
    "srev-066-lowlevel-hotpatch-scan-window.schema.json",
    "generic hack wording",
]:
    require(spec, term, "spec")

for term in [
    "### SREV-066: Low-Level Hotpatch Scan Window",
    "LOWLEVEL_HOTPATCH_SCAN_WINDOW",
    "srev-066-lowlevel-hotpatch-scan-window.schema.json",
]:
    require(ledger, term, "ledger")

print("SREV-066 schema/source gate passed")
