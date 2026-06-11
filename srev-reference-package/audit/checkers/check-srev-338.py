#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-338 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-338 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-338-session-monitor-object-name-staging.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-338 failed: schema is not draft-07")
if schema.get("id") != "SESSION_MONITOR_OBJECT_NAME_STAGING":
    raise SystemExit("SREV-338 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/drv/session.c":
    raise SystemExit("SREV-338 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "bounded local WCHAR staging string",
    "max_buff is a WCHAR count and not a byte count",
    "plus four WCHARs of slack",
    "OBJECT_NAME_INFORMATION Name as a counted UNICODE_STRING",
    "Name Length is a byte count and is converted to WCHAR count",
    "Session_MonitorPutEx uses wcslen when lengths is NULL",
    "this SREV changes comments and proof only",
]:
    require(contracts, term, "schema")

session = (ROOT / "Sandboxie/core/drv/session.c").read_text()
obj_c = (ROOT / "Sandboxie/core/drv/obj.c").read_text()
spec = (ROOT / "docs/plan/srev-338-session-monitor-object-name-staging.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-338.md").read_text()
srev_028 = (ROOT / "docs/plan/ledger/srev-028.md").read_text()
srev_155 = (ROOT / "docs/plan/ledger/srev-155.md").read_text()
srev_160 = (ROOT / "docs/plan/ledger/srev-160.md").read_text()
srev_171 = (ROOT / "docs/plan/ledger/srev-171.md").read_text()
srev_232 = (ROOT / "docs/plan/ledger/srev-232.md").read_text()

put2_start = session.index("_FX NTSTATUS Session_Api_MonitorPut2(")
put2_end = session.index("// Session_Api_MonitorGet", put2_start)
put2 = session[put2_start:put2_end]

putex_start = session.index("_FX void Session_MonitorPutEx(")
putex_end = session.index("// Session_Api_MonitorControl", putex_start)
putex = session[putex_start:putex_end]

obj_name_start = obj_c.index("_FX NTSTATUS Obj_GetNameOrFileName(")
obj_name_end = obj_c.index("// Obj_GetTypeObjectType", obj_name_start)
obj_name = obj_c[obj_name_start:obj_name_end]
obj_get_start = obj_c.index("_FX NTSTATUS Obj_GetName(")
obj_get_end = obj_c.index("// Obj_GetParseName", obj_get_start)
obj_get = obj_c[obj_get_start:obj_get_end]

for term in [
    "log_len = args->log_len.val / sizeof(WCHAR);",
    "ProbeForRead(log_data, log_len * sizeof(WCHAR), sizeof(WCHAR));",
    "const ULONG max_buff = 2048;",
    "SREV-338: `name` is a WCHAR-counted monitor staging buffer.",
    "The +4 allocation slack preserves NUL termination after truncation.",
    "if (log_len > max_buff)\n\t\tlog_len = max_buff;",
    "name = Mem_Alloc(proc->pool, (max_buff + 4) * sizeof(WCHAR));",
    "wmemcpy(name, log_data, log_len);",
    "name[log_len] = L'\\0';",
    "Obj_ObjectTypes[i]",
    "ObReferenceObjectByName(",
    "IoCreateFileSpecifyDeviceObjectHint(",
    "Obj_GetNameOrFileName(\n                                        proc->pool, object, &Name, &NameLength)",
    "log_len = Name->Name.Length / sizeof(WCHAR);",
    "if (log_len > max_buff)\n\t\t\t\t\t\t    log_len = max_buff;",
    "wmemcpy(name, Name->Name.Buffer, log_len);",
    "name[log_len] = L'\\0';",
    "Session_MonitorPutEx(log_type | MONITOR_USER, strings, NULL, proc->pid, PsGetCurrentThreadId());",
    "Mem_Free(name, (max_buff + 4) * sizeof(WCHAR));",
]:
    require(put2, term, "Session_Api_MonitorPut2 block")

for stale in [
    "todo: should we increase this",
    "1028 in buffer",
]:
    reject(put2, stale, "Session_Api_MonitorPut2 block")

for term in [
    "wcslen(strings[i])",
    "lengths ? lengths [i] : wcslen(strings[i])",
    "log_buffer_push_bytes((CHAR*)strings[i], (lengths ? lengths[i] : wcslen(strings[i])) * sizeof(WCHAR)",
]:
    require(putex, term, "Session_MonitorPutEx adjacency")

for term in [
    "NTSTATUS status = Obj_GetName(pool, Object, Name, NameLength);",
    "Obj_GetParseName(",
]:
    require(obj_name, term, "Obj_GetNameOrFileName adjacency")

for term in [
    "OBJECT_NAME_INFORMATION",
    "info->Name.Length",
]:
    require(obj_get, term, "Obj_GetName counted-name adjacency")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "SESSION_MONITOR_ENTRY_HEADER_SIZE",
    "UNICODE_STRING.Length",
    "MaximumLength",
    "byte counts",
]:
    require(srev_028, term, "SREV-028 adjacency")

for term in [
    "OBJECT_NAME_INFORMATION.Name",
    "counted `UNICODE_STRING`",
    "Name->Name.Length",
]:
    require(srev_155, term, "SREV-155 adjacency")

for term in [
    "Obj_ObjectTypes",
    "`Sandboxie/core/drv/session.c` consumes the same table as a NULL-terminated list",
]:
    require(srev_160, term, "SREV-160 adjacency")

for term in [
    "Obj_GetObjectName",
    "named-pipe",
]:
    require(srev_171, term, "SREV-171 adjacency")

for term in [
    "Session_MonitorPutEx",
    "TraceBufferPages",
    "log_buffer_init",
]:
    require(srev_232, term, "SREV-232 adjacency")

for term in [
    "### SREV-338: Session Monitor Object Name Staging",
    "SESSION_MONITOR_OBJECT_NAME_STAGING",
    "srev-338-session-monitor-object-name-staging.schema.json",
    "Sandboxie/core/drv/session.c",
    "Session_Api_MonitorPut2",
    "Session_MonitorPutEx",
    "Obj_GetNameOrFileName",
    "SREV-028",
    "SREV-155",
    "SREV-160",
    "SREV-171",
    "SREV-232",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-338 source gate passed")
