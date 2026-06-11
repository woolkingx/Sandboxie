#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-322 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-322 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-322-proc-werfault-dump-suppression-boundary.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-322 failed: schema is not draft-07")
if schema.get("id") != "PROC_WERFAULT_DUMP_SUPPRESSION_BOUNDARY":
    raise SystemExit("SREV-322 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/dll/proc.c":
    raise SystemExit("SREV-322 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "WerFault dump suppression is local proc.c process-lifetime policy",
    "WER dump configuration and in-process minidump writing are separate owners",
    "first WerFault process may be resumed",
    "repeated WerFault processes may be terminated",
    "keeps PROCESS_INFORMATION handles caller-owned",
    "successful create path",
    "runtime matrix must prove LocalDumps setup",
    "LocalDumps matrix must prove dump capture timing",
    "removes duplicate-path premature handle close",
    "shared user-mode lifecycle capture records must use feature_path werfault-localdumps-boundary",
]:
    require(contracts, term, "schema contracts")

matrix = "\n".join(
    "\n".join(value) if isinstance(value, list) else str(value)
    for value in schema["runtime_capture_matrix"].values()
)
for term in [
    "supported Windows 10 releases",
    "supported Windows 11 releases",
    "global LocalDumps",
    "per-application LocalDumps",
    "DumpFolder",
    "DumpCount",
    "DumpType",
    "CustomDumpFlags",
    "dump folder ACL",
    "WER disabled",
    "automatic debugging configured",
    "EnableMiniDump enabled",
    "EnableMiniDump disabled",
    "blocked write access to dump folder",
    "deterministic native crash",
    "repeated crash in same box",
    "custom crash reporting process",
    "first WerFault process id",
    "duplicate WerFault process ids",
    "first ResumeThread return value",
    "duplicate TerminateProcess result",
    "dump file path",
    "DumpCount replacement behavior",
    "first-path PROCESS_INFORMATION.hProcess validity",
    "duplicate-path PROCESS_INFORMATION.hThread validity",
    "caller GetExitCodeProcess readback",
    "caller WaitForSingleObject readback",
    "SREV-156 Dump_Init path",
    "SREV-237 MiniDumpWriteDump path",
    "automatic debugging suppresses LocalDumps",
    "fresh box first WerFault path is not duplicate-suppressed",
]:
    require(matrix, term, "schema runtime capture matrix")

proc = (ROOT / "Sandboxie/core/dll/proc.c").read_text()
spec = (ROOT / "docs/plan/srev-322-proc-werfault-dump-suppression-boundary.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-322.md").read_text()
srev_156 = (ROOT / "docs/plan/ledger/srev-156.md").read_text()
srev_237 = (ROOT / "docs/plan/ledger/srev-237.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

start = proc.index("if (resume_thread)")
end = proc.index("else {\n\n            //\n            // if the proper token cannot be set", start)
werfault_block = proc[start:end]

for term in [
    "SREV-322: WerFault duplicate-dump suppression boundary.",
    "First WerFault is resumed for WER/LocalDumps capture; later",
    "ones are terminated only after the exact duplicate gate.",
    "if (lpApplicationName && (wcsistr(lpApplicationName, L\"WerFault.exe\")))",
    "if (g_boolWasWerFaultLastProcess == TRUE)",
    "TerminateProcess(lpProcessInformation->hProcess, 1);",
    "WaitForSingleObject(lpProcessInformation->hProcess, 30000);",
    "PROCESS_INFORMATION handles caller-owned",
    "process handle is returned signaled after wait",
    "ResumeThread(lpProcessInformation->hThread);",
    "SbieApi_Log(2224, L\"%S [%S]\", Dll_ImageName, Dll_BoxName);",
    "g_boolWasWerFaultLastProcess = TRUE;",
    "Let WerFault run long enough for WER/LocalDumps to",
]:
    require(werfault_block, term, "WerFault source block")

for stale in [
    "WerFault has some design flaws",
    "If we want crash DMPs we have to make adjustments",
    "Windows will start WerFault 3 times",
    "let WerFault run for a while",
    "handle writeback requires the SREV-322 LocalDumps matrix",
]:
    reject(werfault_block, stale, "WerFault source comment")

duplicate_start = werfault_block.index("if (g_boolWasWerFaultLastProcess == TRUE)")
duplicate_end = werfault_block.index("else", duplicate_start)
duplicate_block = werfault_block[duplicate_start:duplicate_end]
for stale in [
    "CloseHandle(lpProcessInformation->hProcess);",
    "CloseHandle(lpProcessInformation->hThread);",
]:
    reject(duplicate_block, stale, "duplicate WerFault premature handle close")

for term in [
    "DUMP_DBGHELP_ENTRY_AND_CLIENT_POINTERS",
    "MiniDumpWriteDump",
    "EnableMiniDump",
]:
    require(srev_156, term, "SREV-156 dump adjacency")

for term in [
    "DUMP_HEADER_TOPOLOGY_CONTRACT",
    "Dump_Init",
    "MiniDumpWriteDump",
]:
    require(srev_237, term, "SREV-237 dump adjacency")

for term in [
    "PROC_WERFAULT_DUMP_SUPPRESSION_BOUNDARY",
    "Runtime Verification Matrix",
    "LocalDumps Process-Lifetime Matrix",
    "Shared Runtime Capture Evidence",
    "srev-092-322-user-lifecycle-runtime-capture-playbook.md",
    "srev-092-322-user-lifecycle-runtime-capture.schema.json",
    "werfault-localdumps-boundary",
    "Windows gate: validate captured WerFault lifecycle records",
    "`LocalDumps` enabled globally",
    "`EnableMiniDump` on and off",
    "WerFault process ids",
    "automatic debugging",
    "DumpCount",
    "caller-visible `PROCESS_INFORMATION.hProcess`",
    "duplicate process handle remains caller-visible",
    "No predicate, duplicate-state flag, `ResumeThread`, `TerminateProcess`",
    "premature handle close",
]:
    require(spec, term, "spec")

for term in [
    "kind: srev-ledger-entry",
    "id: SREV-322",
    "status: patched-source-level-with-duplicate-werfault-caller-owned-handles-needs-windows-runtime-proof",
    "owner: Sandboxie/core/dll/proc.c",
    "spec: docs/plan/srev-322-proc-werfault-dump-suppression-boundary.md",
    "schema: docs/plan/srev-322-proc-werfault-dump-suppression-boundary.schema.json",
    "checker: docs/plan/check-srev-322.py",
]:
    require(ledger_fragment, term, "ledger fragment header")

for term in [
    "### SREV-322: Proc WerFault Dump Suppression Boundary",
    "PROC_WERFAULT_DUMP_SUPPRESSION_BOUNDARY",
    "WerFault",
    "LocalDumps",
    "EnableMiniDump",
    "output handle behavior",
    "LocalDumps Matrix",
    "automatic-debugger",
]:
    require(ledger, term, "combined ledger")

print("SREV-322 schema/source gate passed")
