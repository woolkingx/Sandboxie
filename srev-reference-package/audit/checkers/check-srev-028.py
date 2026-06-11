#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-028 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-028 failed: {label} still contains {needle!r}")


schema = json.loads((ROOT / "docs/plan/srev-028-monitor-get-entry-size.schema.json").read_text())
if schema.get("id") != "MONITOR_GET_ENTRY_SIZE_SHAPE":
    raise SystemExit("SREV-028 failed: schema missing MONITOR_GET_ENTRY_SIZE_SHAPE")

src = (ROOT / "Sandboxie/core/drv/session.c").read_text()
spec = (ROOT / "docs/plan/srev-028-monitor-get-entry-size.md").read_text()
ledger = read_combined_ledger(ROOT)

for term in [
    "#define SESSION_MONITOR_ENTRY_HEADER_SIZE",
    "SIZE_T entry_size = SESSION_MONITOR_ENTRY_HEADER_SIZE + data_len;",
    "if (entry_size < SESSION_MONITOR_ENTRY_HEADER_SIZE)",
    "ULONG data_size = entry_size - SESSION_MONITOR_ENTRY_HEADER_SIZE;",
    "log_data->MaximumLength < sizeof(WCHAR)",
    "ULONG max_data_size = log_data->MaximumLength - sizeof(WCHAR);",
    "max_data_size &= ~(sizeof(WCHAR) - 1);",
    "ProbeForWrite(log_buffer, data_size + sizeof(WCHAR), sizeof(WCHAR));",
    "log_buffer[data_size / sizeof(WCHAR)] = L'\\0';",
]:
    require(src, term, "driver source")

for stale in [
    "entry_size - (4 + 4 + 4)",
    "MaximumLength - 1",
    "data_size + 1",
    "sizeof(wchar_t)",
]:
    reject(src, stale, "driver source")

for term in [
    "https://learn.microsoft.com/en-us/windows/win32/api/subauth/ns-subauth-unicode_string",
    "https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-probeforwrite",
    "20 header bytes",
    "data_size + sizeof(WCHAR)",
]:
    require(spec, term, "spec")

for term in [
    "### SREV-028: Monitor Get Uses Wrong Entry Payload Size",
    "SESSION_MONITOR_ENTRY_HEADER_SIZE",
    "MaximumLength - sizeof(WCHAR)",
    "entry_size - (4 + 4 + 4)",
]:
    require(ledger, term, "ledger")

print("SREV-028 schema/source gate passed")
