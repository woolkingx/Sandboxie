#!/usr/bin/env python3
import json
from pathlib import Path

from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-232 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-232 failed: stale {label} remains {needle!r}")


def section(text: str, start: str, end: str) -> str:
    start_index = text.index(start)
    end_index = text.index(end, start_index)
    return text[start_index:end_index]


schema = json.loads(
    (ROOT / "docs/plan/srev-232-log-buffer-allocation-size-contract.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-232 failed: schema is not draft-07")
if schema.get("id") != "LOG_BUFFER_ALLOCATION_SIZE_CONTRACT":
    raise SystemExit("SREV-232 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/drv/log_buff.c":
    raise SystemExit("SREV-232 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "flexible-tail LOG_BUFFER object",
    "sizeof(LOG_BUFFER) plus buffer_size",
    "overflow SIZE_T before ExAllocatePoolWithTag",
    "zero byte ring",
    "TraceBufferPages is a page count",
    "must not multiply the byte count by sizeof(WCHAR)",
    "falls back to SESSION_MONITOR_BUF_SIZE",
    "must not dereference Api_LogBuffer",
]:
    require(contracts, term, "schema contract")

spec = (ROOT / "docs/plan/srev-232-log-buffer-allocation-size-contract.md").read_text()
ledger = read_combined_ledger(ROOT)
fragment = (ROOT / "docs/plan/ledger/srev-232.md").read_text()
log_buff_c = (ROOT / "Sandboxie/core/drv/log_buff.c").read_text()
log_buff_h = (ROOT / "Sandboxie/core/drv/log_buff.h").read_text()
session_c = (ROOT / "Sandboxie/core/drv/session.c").read_text()
api_c = (ROOT / "Sandboxie/core/drv/api.c").read_text()
settings = (ROOT / "Sandboxie/install/SbieSettings.ini").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "LOG_BUFFER* log_buffer_init(SIZE_T buffer_size)",
    "SIZE_T alloc_size;",
    "if (buffer_size == 0 || buffer_size > (SIZE_T)-1 - sizeof(LOG_BUFFER))",
    "return NULL;",
    "alloc_size = sizeof(LOG_BUFFER) + buffer_size;",
    "ExAllocatePoolWithTag(PagedPool, alloc_size, tzuk)",
    "ptr_buffer->buffer_size = buffer_size;",
]:
    require(log_buff_c, term, "log_buffer_init allocation gate")

init = section(log_buff_c, "LOG_BUFFER* log_buffer_init", "void log_buffer_free")
if init.index("if (buffer_size == 0") > init.index("ExAllocatePoolWithTag"):
    raise SystemExit("SREV-232 failed: allocation happens before zero/overflow gate")
if init.index("alloc_size = sizeof(LOG_BUFFER) + buffer_size;") > init.index("ExAllocatePoolWithTag"):
    raise SystemExit("SREV-232 failed: allocation happens before named alloc_size")
reject(init, "sizeof(LOG_BUFFER) + buffer_size, tzuk", "inline unchecked allocation")

for term in [
    "#define LOG_BUFFER_SIZE_T ULONG",
    "SIZE_T buffer_size;",
    "SIZE_T buffer_used;",
    "CHAR* buffer_start_ptr;",
    "CHAR buffer_data[0];",
]:
    require(log_buff_h, term, "log buffer schema")

monitor_control = section(
    session_c,
    "_FX NTSTATUS Session_Api_MonitorControl",
    "return STATUS_SUCCESS;\n}"
)
for term in [
    "ULONG BuffPages = Conf_Get_Number(NULL, L\"TraceBufferPages\", 0, 256);",
    "SIZE_T BuffSize = 0;",
    "if (BuffPages <= ((SIZE_T)-1 - sizeof(LOG_BUFFER)) / PAGE_SIZE)",
    "BuffSize = (SIZE_T)BuffPages * PAGE_SIZE;",
    "session->monitor_log = log_buffer_init(BuffSize);",
    "session->monitor_log = log_buffer_init(SESSION_MONITOR_BUF_SIZE);",
]:
    require(monitor_control, term, "session monitor allocation")
reject(monitor_control, "log_buffer_init(BuffSize * sizeof(WCHAR))", "old TraceBufferPages byte doubling")
reject(monitor_control, "log_buffer_init(SESSION_MONITOR_BUF_SIZE * sizeof(WCHAR))", "old fallback byte doubling")

for term in [
    "Api_LogBuffer = log_buffer_init(8 * 8 * 1024);",
    "if (! Api_LogBuffer)\n        return FALSE;",
    "if (!Api_Initialized || !Api_LogBuffer)\n\t\treturn;",
    "if (!Api_LogBuffer)\n        return STATUS_DEVICE_NOT_READY;",
]:
    require(api_c, term, "API log buffer allocation/failure gate")

require(settings, "[TraceBufferPages]", "settings surface")
require(settings, "count of 4K large pages", "TraceBufferPages documented unit")
require(settings, "for a total of 10 MB", "TraceBufferPages example")

for term in [
    "### SREV-232: Log Buffer Allocation Size Contract",
    "LOG_BUFFER_ALLOCATION_SIZE_CONTRACT",
    "Sandboxie/core/drv/log_buff.c",
    "TraceBufferPages",
    "alloc_size",
    "Api_LogBuffer",
    "SESSION_MONITOR_BUF_SIZE",
]:
    require(ledger, term, "combined ledger")

for term in [
    "kind: srev-ledger-entry",
    "id: SREV-232",
    "owner: Sandboxie/core/drv/log_buff.c",
    "patched-source-level-after-official-kernel-allocation-and-safe-integer-review",
    "srev-232-log-buffer-allocation-size-contract.schema.json",
    "check-srev-232.py",
]:
    require(fragment, term, "ledger fragment")
    require(ledger, term, "combined ledger fragment")

print("SREV-232 source gate passed")
