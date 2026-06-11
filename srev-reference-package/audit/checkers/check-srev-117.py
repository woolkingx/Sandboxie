#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-117 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-117 failed: {label} still contains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-117-process-util-allocation-lifetime.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-117 failed: schema is not draft-07")
if schema.get("id") != "PROCESS_UTIL_ALLOCATION_LIFETIME":
    raise SystemExit("SREV-117 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "Mem_Alloc may return NULL",
    "RtlStringCbPrintfW must be allocated before use",
    "Process_LogMessage may skip logging",
    "owns the two-slot thread context until PsCreateSystemThread succeeds",
    "Process_ScheduleKillProc owns and frees",
    "PsCreateSystemThread fails Process_ScheduleKill frees",
    "system-thread handle remains closed",
    "does not change termination policy",
]:
    require(contracts, term, "schema")

source = (ROOT / "Sandboxie/core/drv/process_util.c").read_text()
mem = (ROOT / "Sandboxie/common/pool.c").read_text()
spec = (ROOT / "docs/plan/srev-117-process-util-allocation-lifetime.md").read_text()
ledger = read_combined_ledger(ROOT)

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

require(mem, "return NULL;", "pool allocation failure shape")
require(mem, "return ptr;", "pool allocation return shape")

log_start = source.index("_FX void Process_LogMessage(")
log_end = source.index("// Process_TrackProcessLimit", log_start)
log_func = source[log_start:log_end]
for term in [
    "WCHAR *text = Mem_Alloc(proc->pool, len);",
    "if (! text)\n        return;",
    "RtlStringCbPrintfW(text, len, L\"%s [%s]\", proc->image_name, box->name);",
    "Log_MsgP1(msgid, text, proc->pid);",
    "Mem_Free(text, len);",
]:
    require(log_func, term, "Process_LogMessage")
if log_func.index("if (! text)") > log_func.index("RtlStringCbPrintfW(text"):
    raise SystemExit("SREV-117 failed: Process_LogMessage allocation gate is after use")

worker_start = source.index("_FX VOID Process_ScheduleKillProc(")
worker_end = source.index("// Process_ScheduleKill", worker_start)
worker_func = source[worker_start:worker_end]
for term in [
    "PVOID* params = (PVOID*)StartContext;",
    "HANDLE process_id = (HANDLE)(params[0]);",
    "LONG delay_ms = (LONG)(params[1]);",
    "Mem_Free(params, sizeof(PVOID)*2);",
    "PsTerminateSystemThread(status);",
]:
    require(worker_func, term, "Process_ScheduleKillProc")
if worker_func.index("Mem_Free(params, sizeof(PVOID)*2);") > worker_func.index("PsLookupProcessByProcessId"):
    raise SystemExit("SREV-117 failed: worker context free moved after process work")

kill_start = source.index("_FX BOOLEAN Process_ScheduleKill(")
kill_func = source[kill_start:]
for term in [
    "PVOID *params = Mem_Alloc(Driver_Pool, sizeof(PVOID)*2);",
    "if (! params)\n        return FALSE;",
    "params[0] = proc->pid;",
    "params[1] = (PVOID)delay_ms;",
    "status = PsCreateSystemThread(&handle, THREAD_ALL_ACCESS, &objattrs, NULL, NULL, Process_ScheduleKillProc, params);",
    "ZwClose(handle);",
    "return TRUE;",
    "Mem_Free(params, sizeof(PVOID)*2);\n    return FALSE;",
]:
    require(kill_func, term, "Process_ScheduleKill")
if kill_func.index("if (! params)") > kill_func.index("params[0] = proc->pid;"):
    raise SystemExit("SREV-117 failed: params allocation gate is after write")
if kill_func.index("Mem_Free(params, sizeof(PVOID)*2);\n    return FALSE;") < kill_func.index("PsCreateSystemThread"):
    raise SystemExit("SREV-117 failed: params free must be on thread-create failure path")

reject(kill_func, "PVOID *params = Mem_Alloc(Driver_Pool, sizeof(PVOID)*2);\n    params[0]", "unguarded params allocation")

for term in [
    "### SREV-117: Process Util Allocation Lifetime",
    "PROCESS_UTIL_ALLOCATION_LIFETIME",
    "srev-117-process-util-allocation-lifetime.schema.json",
    "Sandboxie/core/drv/process_util.c",
    "Process_LogMessage",
    "Process_ScheduleKill",
    "Process_ScheduleKillProc",
    "PsCreateSystemThread",
    "Mem_Free(params, sizeof(PVOID)*2)",
]:
    require(ledger, term, "ledger")

print("SREV-117 schema/source gate passed")
