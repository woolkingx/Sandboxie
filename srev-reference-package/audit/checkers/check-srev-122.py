#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-122 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-122 failed: {label} still contains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-122-process-force-map-allocation-lifetime.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-122 failed: schema is not draft-07")
if schema.get("id") != "PROCESS_FORCE_MAP_ALLOCATION_LIFETIME":
    raise SystemExit("SREV-122 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "Mem_Alloc may return NULL",
    "Process_DfpInsert PROCESS_TERMINATED owns Process_ListLock and IRQL restoration on allocation failure",
    "Process_DfpInsert parent-child path is called with the process list already locked",
    "Process_DfpInsert parent-child allocation failure returns FALSE without inserting a map record",
    "Process_FcpInsert owns Process_ListLock and IRQL restoration on allocation failure",
    "DFP and FCP record fields are written only after allocation succeeds",
]:
    require(contracts, term, "schema")

source = (ROOT / "Sandboxie/core/drv/process_force.c").read_text()
mem = (ROOT / "Sandboxie/common/pool.c").read_text()
spec = (ROOT / "docs/plan/srev-122-process-force-map-allocation-lifetime.md").read_text()
ledger = read_combined_ledger(ROOT)

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

require(mem, "return NULL;", "pool allocation failure shape")
require(mem, "return ptr;", "pool allocation return shape")

dfp = source[
    source.index("_FX BOOLEAN Process_DfpInsert"):
    source.index("// Process_DfpDelete")
]
for term in [
    "proc = Mem_Alloc(Driver_Pool, sizeof(FORCE_PROCESS_2));\n        if (! proc) {\n            ExReleaseResourceLite(Process_ListLock);\n            KeLowerIrql(irql);\n            return FALSE;\n        }",
    "proc->pid = ProcessId;",
    "proc->silent = FALSE;",
    "map_insert(&Process_MapDfp, ProcessId, proc, 0);",
    "proc = Mem_Alloc(Driver_Pool, sizeof(FORCE_PROCESS_2));\n            if (! proc)\n                return FALSE;",
]:
    require(dfp, term, "Process_DfpInsert")

if dfp.index("if (! proc) {\n            ExReleaseResourceLite(Process_ListLock);") > dfp.index("proc->pid = ProcessId;"):
    raise SystemExit("SREV-122 failed: PROCESS_TERMINATED DFP allocation gate is after field write")
if dfp.index("if (! proc)\n                return FALSE;") > dfp.rindex("proc->pid = ProcessId;"):
    raise SystemExit("SREV-122 failed: parent-child DFP allocation gate is after field write")
reject(dfp, "proc = Mem_Alloc(Driver_Pool, sizeof(FORCE_PROCESS_2));\n        proc->pid = ProcessId;", "unguarded PROCESS_TERMINATED DFP allocation")
reject(dfp, "proc = Mem_Alloc(Driver_Pool, sizeof(FORCE_PROCESS_2));\n            proc->pid = ProcessId;", "unguarded parent-child DFP allocation")

fcp = source[
    source.index("_FX VOID Process_FcpInsert"):
    source.index("// Process_FcpDelete")
]
for term in [
    "proc = Mem_Alloc(Driver_Pool, sizeof(FORCE_PROCESS_3));\n    if (! proc) {\n        ExReleaseResourceLite(Process_ListLock);\n        KeLowerIrql(irql);\n        return;\n    }",
    "proc->pid = ProcessId;",
    "wmemcpy(proc->boxname, boxname, BOXNAME_COUNT);",
    "map_insert(&Process_MapFcp, ProcessId, proc, 0);",
]:
    require(fcp, term, "Process_FcpInsert")
if fcp.index("if (! proc) {\n        ExReleaseResourceLite(Process_ListLock);") > fcp.index("proc->pid = ProcessId;"):
    raise SystemExit("SREV-122 failed: FCP allocation gate is after field write")
reject(fcp, "proc = Mem_Alloc(Driver_Pool, sizeof(FORCE_PROCESS_3));\n    proc->pid = ProcessId;", "unguarded FCP allocation")

for term in [
    "### SREV-122: Process Force Map Allocation Lifetime",
    "PROCESS_FORCE_MAP_ALLOCATION_LIFETIME",
    "srev-122-process-force-map-allocation-lifetime.schema.json",
    "Sandboxie/core/drv/process_force.c",
    "Process_DfpInsert",
    "Process_FcpInsert",
    "Process_MapDfp",
    "Process_MapFcp",
    "Mem_Alloc",
    "ExReleaseResourceLite",
    "KeLowerIrql",
]:
    require(ledger, term, "ledger")

print("SREV-122 schema/source gate passed")
