#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-162 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-162 failed: {label} still contains {needle!r}")


def section(text: str, start: str, end: str) -> str:
    start_index = text.index(start)
    end_index = text.index(end, start_index)
    return text[start_index:end_index]


schema = json.loads(
    (ROOT / "docs/plan/srev-162-driver-event-log-entry-size-gate.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-162 failed: schema is not draft-07")
if schema.get("id") != "DRIVER_EVENT_LOG_ENTRY_SIZE_GATE":
    raise SystemExit("SREV-162 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "log.c owns the driver event-log packet construction path",
    "IoAllocateErrorLogEntry is the kernel DDI boundary and accepts a UCHAR entry size",
    "event-log EntrySize must be proven strictly less than ERROR_LOG_MAXIMUM_SIZE before casting to UCHAR",
    "insertion strings must be null-terminated within the remaining packet budget before any copy into IO_ERROR_LOG_PACKET storage",
    "RtlStringCbLengthW is the bounded local string-length gate for this path",
    "does not change Sandboxie policy popup logging service wakeup message ids monitor logging or Api_AddMessage wire shape",
    "Linux source gate is not Windows driver build or runtime proof",
]:
    require(contracts, term, "schema")

source = (ROOT / "Sandboxie/core/drv/log.c").read_text()
header = (ROOT / "Sandboxie/core/drv/log.h").read_text()
spec = (ROOT / "docs/plan/srev-162-driver-event-log-entry-size-gate.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-162.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "void Log_Msg(",
    "void Log_Msg_Process(",
    "void Log_Popup_MsgEx(",
    "#define Log_Msg0(error_code)",
]:
    require(header, term, "log.h API surface")

helper = section(source, "_FX BOOLEAN Log_GetEventStringBytes", "_FX void Log_Event_Msg")
for term in [
    "*string_bytes = 0;",
    "if (! string)",
    "if (max_bytes < sizeof(WCHAR))",
    "RtlStringCbLengthW(string, max_bytes, &length);",
    "if (! NT_SUCCESS(status))",
    "if (length > max_bytes - sizeof(WCHAR))",
    "*string_bytes = length + sizeof(WCHAR);",
]:
    require(helper, term, "Log_GetEventStringBytes")
reject(helper, "wcslen", "bounded event string helper")

event = section(source, "_FX void Log_Event_Msg", "//---------------------------------------------------------------------------\n// Log_Popup_Msg")
for term in [
    "SIZE_T entry_size;",
    "SIZE_T max_strings_len;",
    "SIZE_T string1_len;",
    "SIZE_T string2_len;",
    "if (sizeof(IO_ERROR_LOG_PACKET) >= ERROR_LOG_MAXIMUM_SIZE)",
    "max_strings_len = (ERROR_LOG_MAXIMUM_SIZE - 1) - sizeof(IO_ERROR_LOG_PACKET);",
    "if (! Log_GetEventStringBytes(string1, max_strings_len, &string1_len))",
    "if (! Log_GetEventStringBytes(string2, max_strings_len - string1_len, &string2_len))",
    "entry_size = sizeof(IO_ERROR_LOG_PACKET) + string1_len + string2_len;",
    "if (entry_size < ERROR_LOG_MAXIMUM_SIZE) {",
    "IoAllocateErrorLogEntry(",
    "(UCHAR)entry_size",
    "memcpy(strings, string1, string1_len);",
    "memcpy(strings, string2, string2_len);",
    "IoWriteErrorLogEntry(entry);",
]:
    require(event, term, "Log_Event_Msg")
reject(event, "wcslen(string1)", "event-log unbounded string1 length")
reject(event, "wcslen(string2)", "event-log unbounded string2 length")
reject(event, "entry_size <= ERROR_LOG_MAXIMUM_SIZE", "inclusive UCHAR size gate")
reject(event, "int entry_size", "event-log integer size")

if event.index("if (entry_size < ERROR_LOG_MAXIMUM_SIZE)") > event.index("IoAllocateErrorLogEntry("):
    raise SystemExit("SREV-162 failed: EntrySize gate is after IoAllocateErrorLogEntry")
if event.index("Log_GetEventStringBytes(string1") > event.index("memcpy(strings, string1"):
    raise SystemExit("SREV-162 failed: string1 is copied before bounded length proof")
if event.index("Log_GetEventStringBytes(string2") > event.index("memcpy(strings, string2"):
    raise SystemExit("SREV-162 failed: string2 is copied before bounded length proof")

for term in [
    "### SREV-162: Driver Event Log Entry Size Gate",
    "DRIVER_EVENT_LOG_ENTRY_SIZE_GATE",
    "srev-162-driver-event-log-entry-size-gate.schema.json",
    "Sandboxie/core/drv/log.h",
    "Sandboxie/core/drv/log.c",
    "IoAllocateErrorLogEntry",
    "IO_ERROR_LOG_PACKET",
    "RtlStringCbLengthW",
    "entry_size < ERROR_LOG_MAXIMUM_SIZE",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-162 schema/source gate passed")
