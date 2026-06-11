#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-078 failed: {label} missing {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-078-sysinfo-hidehostprocess-list.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-078 failed: schema is not draft-07")
if schema.get("id") != "SYSINFO_HIDEHOSTPROCESS_LIST_CAPACITY":
    raise SystemExit("SREV-078 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "double-NUL-terminated WCHAR multi-string",
    "capacity grows to fit configured HideHostProcess entries",
    "HeapReAlloc failure preserves the old list",
    "used length plus new entry plus final terminator",
    "consumer iteration walks initialized entries",
]:
    require(contracts, term, "schema")

src = (ROOT / "Sandboxie/core/dll/sysinfo.c").read_text()
spec = (ROOT / "docs/plan/srev-078-sysinfo-hidehostprocess-list.md").read_text()
ledger = read_combined_ledger(ROOT)

start = src.index("_FX void SysInfo_DiscardProcesses")
end = src.index("// SysInfo_SetLocaleInfoW", start)
func = src[start:end]

for term in [
    "WCHAR* hiddenProcesses = NULL;",
    "WCHAR* hiddenProcessesPtr = NULL;",
    "ULONG hiddenProcessesLen = 0;",
    "ULONG hiddenProcessesUsed = 0;",
    "ULONG nameLen = wcslen(hiddenProcess) + 1;",
    "if (hiddenProcessesUsed > (ULONG)-1 - nameLen - 1)",
    "ULONG requiredLen = hiddenProcessesUsed + nameLen + 1;",
    "ULONG newLen = hiddenProcessesLen ? hiddenProcessesLen : 16 * 110;",
    "while (newLen < requiredLen) {",
    "if (newLen > (ULONG)-1 / 2) {",
    "HeapReAlloc(GetProcessHeap(), 0, hiddenProcesses, newLen * sizeof(WCHAR))",
    "HeapAlloc(GetProcessHeap(), 0, newLen * sizeof(WCHAR))",
    "if (!newHiddenProcesses)\n\t\t\t\t\tbreak;",
    "hiddenProcessesPtr = hiddenProcesses + hiddenProcessesUsed;",
    "wmemcpy(hiddenProcessesPtr, hiddenProcess, nameLen);",
    "hiddenProcessesUsed += nameLen;",
    "hiddenProcesses[hiddenProcessesUsed] = L'\\0';",
    "for (hiddenProcessesPtr = hiddenProcesses; *hiddenProcessesPtr != L'\\0'; hiddenProcessesPtr += wcslen(hiddenProcessesPtr) + 1)",
    "HeapFree(GetProcessHeap(), 0, hiddenProcesses);",
]:
    require(func, term, "SysInfo_DiscardProcesses source")

for stale in [
    "100 * 110; // we can hide up to 100 processes, should be enough",
    "SbieApi_Log(2310, L\", 'HideProcess'\"); // todo add custom message",
]:
    if stale in func:
        raise SystemExit(f"SREV-078 failed: stale fixed-capacity path remains: {stale}")

if func.index("if (requiredLen > hiddenProcessesLen)") > func.index("wmemcpy(hiddenProcessesPtr, hiddenProcess, nameLen);"):
    raise SystemExit("SREV-078 failed: copy occurs before capacity gate")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "### SREV-078: SysInfo HideHostProcess List Capacity",
    "SYSINFO_HIDEHOSTPROCESS_LIST_CAPACITY",
    "srev-078-sysinfo-hidehostprocess-list.schema.json",
]:
    require(ledger, term, "ledger")

print("SREV-078 schema/source gate passed")
