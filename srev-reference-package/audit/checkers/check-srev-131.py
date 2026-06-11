#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-131 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-131 failed: {label} still contains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-131-process-findsandboxed-lock-release.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-131 failed: schema is not draft-07")
if schema.get("id") != "PROCESS_FINDSANDBOXED_LOCK_RELEASE":
    raise SystemExit("SREV-131 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "Process_Find owns the Process_ListLock and raised-IRQL transfer contract when out_irql is non-null",
    "Process_Find raises to APC_LEVEL and acquires Process_ListLock before returning a protected PROCESS pointer",
    "Process_Find without out_irql releases Process_ListLock and lowers IRQL before return",
    "Process_Find with out_irql stores the old IRQL for the caller and leaves Process_ListLock held",
    "Process_FindSandboxed may filter a found PROCESS when bHostInject is set",
    "Process_FindSandboxed returning NULL after bHostInject filtering releases Process_ListLock when out_irql is non-null",
    "Process_FindSandboxed returning NULL after bHostInject filtering lowers IRQL using the old IRQL from out_irql",
    "Process_FindSandboxed preserves PROCESS_TERMINATED sentinel behavior",
]:
    require(contracts, term, "schema")

source = (ROOT / "Sandboxie/core/drv/process.c").read_text()
header = (ROOT / "Sandboxie/core/drv/process.h").read_text()
spec = (ROOT / "docs/plan/srev-131-process-findsandboxed-lock-release.md").read_text()
ledger = read_combined_ledger(ROOT)

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

process_find = source[
    source.index("_FX PROCESS *Process_Find(HANDLE ProcessId, KIRQL *out_irql)"):
    source.index("//---------------------------------------------------------------------------\n// Process_FindSandboxed")
]
find_sandboxed = source[
    source.index("_FX PROCESS *Process_FindSandboxed(HANDLE ProcessId, KIRQL *out_irql)"):
    source.index("#endif", source.index("_FX PROCESS *Process_FindSandboxed"))
]

for term in [
    "KeRaiseIrql(APC_LEVEL, &irql);",
    "ExAcquireResourceSharedLite(Process_ListLock, TRUE);",
    "proc = map_get(&Process_Map, ProcessId);",
    "proc = PROCESS_TERMINATED;",
    "if (out_irql) {",
    "*out_irql = irql;",
    "ExReleaseResourceLite(Process_ListLock);",
    "KeLowerIrql(irql);",
]:
    require(process_find, term, "Process_Find")

if process_find.index("*out_irql = irql;") > process_find.index("} else {", process_find.index("if (out_irql) {")):
    raise SystemExit("SREV-131 failed: Process_Find out_irql transfer is after local release branch")

for term in [
    "PROCESS* proc = Process_Find(ProcessId, out_irql);",
    "if (proc && proc != PROCESS_TERMINATED)",
    "if (proc->bHostInject)",
    "if (out_irql) {",
    "ExReleaseResourceLite(Process_ListLock);",
    "KeLowerIrql(*out_irql);",
    "proc = NULL;",
    "return proc;",
]:
    require(find_sandboxed, term, "Process_FindSandboxed")

release_at = find_sandboxed.index("ExReleaseResourceLite(Process_ListLock);")
lower_at = find_sandboxed.index("KeLowerIrql(*out_irql);")
null_at = find_sandboxed.index("proc = NULL;")
if not (release_at < lower_at < null_at):
    raise SystemExit("SREV-131 failed: release/lower must happen before filtered NULL return")

reject(
    find_sandboxed,
    "if (proc->bHostInject)\n        {\n            proc = NULL;\n        }",
    "stale filtered host-inject NULL without release",
)

for term in [
    "#define PROCESS_TERMINATED",
    "PROCESS *Process_Find(HANDLE ProcessId, KIRQL *out_irql);",
    "PROCESS *Process_FindSandboxed(HANDLE ProcessId, KIRQL *out_irql);",
    "extern PERESOURCE Process_ListLock;",
]:
    require(header, term, "process.h")

for term in [
    "### SREV-131: Process FindSandboxed Lock Release",
    "PROCESS_FINDSANDBOXED_LOCK_RELEASE",
    "srev-131-process-findsandboxed-lock-release.schema.json",
    "Sandboxie/core/drv/process.h",
    "Sandboxie/core/drv/process.c",
    "Process_FindSandboxed",
    "Process_Find",
    "Process_ListLock",
    "KeRaiseIrql",
    "KeLowerIrql",
    "ExReleaseResourceLite",
    "bHostInject",
    "PROCESS_TERMINATED",
]:
    require(ledger, term, "ledger")

print("SREV-131 schema/source gate passed")
