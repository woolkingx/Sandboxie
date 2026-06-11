#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-100 failed: {label} missing {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-100-process-create-caller-snapshot.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-100 failed: schema is not draft-07")
if schema.get("id") != "PROCESS_CREATE_CALLER_SNAPSHOT":
    raise SystemExit("SREV-100 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "ParentProcessId is the inherited parent process",
    "not necessarily the creator process",
    "CreatingThreadId.UniqueProcess is the official creator/caller process id",
    "legacy PsSetCreateProcessNotifyRoutine",
    "keeps PsGetCurrentProcessId as CallerId",
    "Process_Find with out_irql returns while holding Process_ListLock shared",
    "clone parent_proc->box before releasing Process_ListLock",
    "Process_Delete removes and frees PROCESS state only after acquiring Process_ListLock exclusive",
    "must not dereference parent_proc after Process_ListLock is released",
    "stable sandbox-state snapshot contract",
]:
    require(contracts, term, "schema")

process = (ROOT / "Sandboxie/core/drv/process.c").read_text()
process_h = (ROOT / "Sandboxie/core/drv/process.h").read_text()
spec = (ROOT / "docs/plan/srev-100-process-create-caller-snapshot.md").read_text()
ledger = read_combined_ledger(ROOT)

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "static void Process_NotifyProcessEx(\n    PEPROCESS Process, HANDLE ProcessId, PPS_CREATE_NOTIFY_INFO CreateInfo);",
    "PsSetCreateProcessNotifyRoutineEx(Process_NotifyProcessEx, FALSE)",
    "PsSetCreateProcessNotifyRoutine(Process_NotifyProcess, FALSE)",
    "Process_NotifyProcess_Create(ProcessId, ParentId, PsGetCurrentProcessId(), NULL, 0, NULL)",
    "CreateInfo->CreatingThreadId.UniqueProcess",
    "Process_NotifyProcess_Create(ProcessId, CreateInfo->ParentProcessId, CreateInfo->CreatingThreadId.UniqueProcess, Name, NameLength, NULL)",
    "Process_Find(CallerId, &irql)",
    "parent_proc = Process_Find(ParentId, &irql)",
    "box = Box_Clone(Driver_Pool, parent_proc->box)",
    "ExReleaseResourceLite(Process_ListLock);\n        KeLowerIrql(irql);",
    "Process_Create(ProcessId, box, ImagePath, &irql)",
    "map_take(&Process_Map, ProcessId, &proc, 0)",
    "Pool_Delete(proc->pool)",
]:
    require(process, term, "process.c source shape")

for stale in [
    "cause us to crash",
]:
    if stale in process:
        raise SystemExit(f"SREV-100 failed: stale wording remains {stale!r}")

snapshot_start = process.index("if (parent_proc && !parent_proc->bHostInject) {")
snapshot_end = process.index("// 3.  if parent process is not sandboxed", snapshot_start)
snapshot_block = process[snapshot_start:snapshot_end]
if snapshot_block.index("box = Box_Clone(Driver_Pool, parent_proc->box)") > snapshot_block.index("} else\n                create_terminated = TRUE;"):
    raise SystemExit("SREV-100 failed: parent box clone is not inside guarded snapshot block")

post_snapshot = process[snapshot_end:process.index("#ifdef DRV_BREAKOUT", snapshot_end)]
if "parent_proc->" in post_snapshot:
    raise SystemExit("SREV-100 failed: parent box clone is not before process-list release")

for term in [
    "stable snapshot of its sandbox state",
    "Process_Find finds the PROCESS block",
    "Process_NotifyProcess_Create(",
]:
    require(process + process_h, term, "local process contract")

for term in [
    "ParentProcessId",
    "CreatingThreadId.UniqueProcess",
    "Process_ListLock",
    "Box_Clone",
    "Process_Delete",
    "Driver Verifier",
]:
    require(spec, term, "spec shape")

for term in [
    "### SREV-100: Process Create Caller Snapshot",
    "PROCESS_CREATE_CALLER_SNAPSHOT",
    "srev-100-process-create-caller-snapshot.schema.json",
]:
    require(ledger, term, "ledger")

print("SREV-100 schema/source gate passed")
