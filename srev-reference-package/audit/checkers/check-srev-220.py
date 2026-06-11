#!/usr/bin/env python3
import json
from pathlib import Path

from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-220 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-220 failed: stale {label} remains {needle!r}")


def between(text: str, start: str, end: str) -> str:
    a = text.index(start)
    b = text.index(end, a + len(start))
    return text[a:b]


schema = json.loads(
    (ROOT / "docs/plan/srev-220-session-monitor-get2-buffer-floor.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-220 failed: schema is not draft-07")
if schema.get("id") != "SESSION_MONITOR_GET2_BUFFER_FLOOR":
    raise SystemExit("SREV-220 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/drv/session.h":
    raise SystemExit("SREV-220 failed: wrong owner")
if schema.get("implementation") != "Sandboxie/core/drv/session.c":
    raise SystemExit("SREV-220 failed: wrong implementation")

contracts = "\n".join(schema["contracts"])
for term in [
    "session monitor API surface",
    "size-prefixed entries terminated by one zero LOG_BUFFER_SIZE_T",
    "at least sizeof(LOG_BUFFER_SIZE_T)",
    "buffer_len is an in/out user ULONG pointer",
    "reserves one trailing LOG_BUFFER_SIZE_T slot",
    "Windows monitor runtime proof",
]:
    require(contracts, term, "schema contract")

spec = (ROOT / "docs/plan/srev-220-session-monitor-get2-buffer-floor.md").read_text()
header = (ROOT / "Sandboxie/core/drv/session.h").read_text()
source = (ROOT / "Sandboxie/core/drv/session.c").read_text()
api_defs = (ROOT / "Sandboxie/core/drv/api_defs.h").read_text()
log_buff = (ROOT / "Sandboxie/core/drv/log_buff.h").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-220.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "void Session_MonitorPut(ULONG type, const WCHAR *name, HANDLE pid);",
    "void Session_MonitorPutEx(ULONG type, const WCHAR** strings, ULONG* lengths, HANDLE pid, HANDLE tid);",
    "extern volatile LONG Session_MonitorCount;",
]:
    require(header, term, "session.h monitor surface")

for term in [
    "API_ARGS_BEGIN(API_MONITOR_GET2_ARGS)",
    "API_ARGS_FIELD(WCHAR *, buffer_ptr)",
    "API_ARGS_FIELD(ULONG *, buffer_len)",
    "API_ARGS_CLOSE(API_MONITOR_GET2_ARGS)",
]:
    require(api_defs, term, "API_MONITOR_GET2_ARGS")

require(log_buff, "#define LOG_BUFFER_SIZE_T ULONG", "log buffer size type")

for term in [
    "Api_SetFunction(API_MONITOR_GET2,            Session_Api_MonitorGet2);",
    "_FX NTSTATUS Session_Api_MonitorGet2(PROCESS *proc, ULONG64 *parms)",
]:
    require(source, term, "monitor get2 registration")

body = between(
    source,
    "_FX NTSTATUS Session_Api_MonitorGet2(PROCESS *proc, ULONG64 *parms)",
    "\n    return status;\n}",
)
for term in [
    "ProbeForRead(args->buffer_len.val, sizeof(ULONG), sizeof(ULONG));",
    "buffer_len = *args->buffer_len.val;",
    "ProbeForWrite(args->buffer_len.val, sizeof(ULONG), sizeof(ULONG));",
    "*args->buffer_len.val = 0;",
    "if (buffer_len < sizeof(LOG_BUFFER_SIZE_T))\n        return STATUS_BUFFER_TOO_SMALL;",
    "ProbeForWrite(args->buffer_ptr.val, buffer_len, sizeof(UCHAR));",
    "if (entry_size > buffer_len - sizeof(LOG_BUFFER_SIZE_T))",
    "*(LOG_BUFFER_SIZE_T*)buffer_ptr = 0;",
    "*args->buffer_len.val = (ULONG)(buffer_ptr - (UCHAR*)args->buffer_ptr.val);",
]:
    require(body, term, "Session_Api_MonitorGet2")

if not (
    body.index("*args->buffer_len.val = 0;")
    < body.index("if (buffer_len < sizeof(LOG_BUFFER_SIZE_T))")
    < body.index("ProbeForWrite(args->buffer_ptr.val, buffer_len, sizeof(UCHAR));")
    < body.index("if (entry_size > buffer_len - sizeof(LOG_BUFFER_SIZE_T))")
    < body.index("*(LOG_BUFFER_SIZE_T*)buffer_ptr = 0;")
):
    raise SystemExit("SREV-220 failed: MonitorGet2 buffer floor/order is wrong")

for term in [
    "kind: srev-ledger-entry",
    "id: SREV-220",
    "owner: Sandboxie/core/drv/session.h",
    "implementation: Sandboxie/core/drv/session.c",
    "spec: docs/plan/srev-220-session-monitor-get2-buffer-floor.md",
    "schema: docs/plan/srev-220-session-monitor-get2-buffer-floor.schema.json",
    "checker: docs/plan/check-srev-220.py",
    "patched-source-level-after-official-probeforwrite-and-local-log-buffer-wire-review",
]:
    require(ledger_fragment, term, "ledger fragment")
    require(ledger, term, "combined ledger")

print("SREV-220 source gate passed")
