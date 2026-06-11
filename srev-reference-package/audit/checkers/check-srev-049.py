#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-049 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-049 failed: {label} still contains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-049-com-closedrt-list.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-049 failed: schema is not draft-07")
if schema.get("id") != "COM_CLOSED_RT_MULTI_STRING":
    raise SystemExit("SREV-049 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "cached ClosedRT runtime-class list",
    "WCHAR multi-string with an empty final string",
    "first WCHAR is initialized to NUL",
    "leaves room for the final empty string",
    "configuration drift",
    "WindowsGetStringRawBuffer",
]:
    require(contracts, term, "schema")

src = (ROOT / "Sandboxie/core/dll/com.c").read_text()
spec = (ROOT / "docs/plan/srev-049-com-closedrt-list.md").read_text()
ledger = read_combined_ledger(ROOT)

start = src.index("_FX void Com_LoadRTList(")
end = src.index("// Com_IsClosedRT", start)
load_rt = src[start:end]

for term in [
    "(*pNames)[0] = L'\\0';",
    "ULONG entry_len;",
    "entry_len = (ULONG)wcslen(buf) + 1;",
    "if (entry_len >= total_len - cur_pos)",
    "break;",
    "cur_pos += entry_len;",
    "(*pNames)[cur_pos] = L'\\0';",
]:
    require(load_rt, term, "Com_LoadRTList")

reject(load_rt, "(*pNames)[total_len - 1] = L'\\0';", "Com_LoadRTList")

for term in [
    "https://learn.microsoft.com/en-us/windows/win32/api/roapi/nf-roapi-rogetactivationfactory",
    "https://learn.microsoft.com/en-us/windows/win32/winrt/hstring",
    "srev-049-com-closedrt-list.schema.json",
]:
    require(spec, term, "spec")

for term in [
    "### SREV-049: COM ClosedRT Multi-String Drift",
    "COM_CLOSED_RT_MULTI_STRING",
    "srev-049-com-closedrt-list.schema.json",
]:
    require(ledger, term, "ledger")

print("SREV-049 schema/source gate passed")
