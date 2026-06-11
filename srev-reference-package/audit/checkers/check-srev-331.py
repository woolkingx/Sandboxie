#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-331 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-331 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-331-file-flt-spooler-probe-exceptions.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-331 failed: schema is not draft-07")
if schema.get("id") != "FILE_FLT_SPOOLER_PROBE_EXCEPTIONS":
    raise SystemExit("SREV-331 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/drv/file_flt.c":
    raise SystemExit("SREV-331 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "file_flt.c owns the spoolsv impersonated write deny gate",
    "spooler probe exceptions remain scoped to spoolsv.exe generic-write create requests",
    "target names ending in ':' fall through",
    "tpwinprn-stat.txt remains a printer-driver status probe exception",
    "\\pipe\\spoolss remains a spooler pipe exception",
    "AllowSpoolerPrintToFile and spooler_directory behavior remain unchanged",
    "this SREV changes comments and proof only",
]:
    require(contracts, term, "schema")

src = (ROOT / "Sandboxie/core/drv/file_flt.c").read_text()
spec = (ROOT / "docs/plan/srev-331-file-flt-spooler-probe-exceptions.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-331.md").read_text()

start = src.index("Block write operations from a system account process")
end = src.index("File_RenameOperation(proc, Iopb, TRUE);", start)
block = src[start:end]

for term in [
    "IRP_MJ_CREATE",
    "SBIE_FILE_GENERIC_WRITE",
    "MyIsProcessRunningAsSystemAccount(PsGetCurrentProcessId())",
    "_wcsicmp(nptr, L\"spoolsv.exe\") == 0",
    "UnicodeStringEndsWith(&Iopb->TargetFileObject->FileName, L\":\"",
    "SearchUnicodeString(&Iopb->TargetFileObject->FileName, L\"tpwinprn-stat.txt\"",
    "SearchUnicodeString(&Iopb->TargetFileObject->FileName, L\"\\\\pipe\\\\spoolss\"",
    "GetThreadTokenOwnerPid()",
    "Process_Find((HANDLE)ulOwnerPid, NULL)",
    "proc && !proc->terminated && !proc->ipc_allowSpoolerPrintToFile",
    "proc->box->spooler_directory",
    "status = File_CreateOperation(proc, Iopb, &usTargetFile);",
    "SREV-331: let spooler/port-monitor probe names that end",
    "not sandbox denial, owns the failure status.",
    "SREV-331: keep this printer-driver status probe outside the",
    "print-to-file deny path; the spooler compatibility branch",
]:
    require(block, term, "spooler deny block")

for stale in [
    "Stupid hack",
    "another stupid hack",
    "make spoolsv happy",
    "humor it",
]:
    reject(block, stale, "spooler probe comment")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "### SREV-331: File Filter Spooler Probe Exceptions",
    "FILE_FLT_SPOOLER_PROBE_EXCEPTIONS",
    "srev-331-file-flt-spooler-probe-exceptions.schema.json",
    "Sandboxie/core/drv/file_flt.c",
    "spoolsv.exe",
    "tpwinprn-stat.txt",
    "\\pipe\\spoolss",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-331 source gate passed")
