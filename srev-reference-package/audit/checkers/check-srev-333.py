#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-333 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-333 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-333-file-flt-kaspersky-swmon-sentinel.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-333 failed: schema is not draft-07")
if schema.get("id") != "FILE_FLT_KASPERSKY_SWMON_SENTINEL":
    raise SystemExit("SREV-333 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/drv/file_flt.c":
    raise SystemExit("SREV-333 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "early x64 pre-SbieDll-loaded swmon_*_kl1 sentinel",
    "does not own NtSetInformationThread semantics",
    "STATUS_BAD_INITIAL_PC remains the local non-canceling sentinel",
    "component prefix \\swmon_ and suffix _kl1",
    "SREV-329 owns the adjacent SbieDll NtSetInformationThread pass-through guard",
    "this SREV changes comments and proof only",
]:
    require(contracts, term, "schema")

file_flt = (ROOT / "Sandboxie/core/drv/file_flt.c").read_text()
syscall_open = (ROOT / "Sandboxie/core/drv/syscall_open.c").read_text()
spec = (ROOT / "docs/plan/srev-333-file-flt-kaspersky-swmon-sentinel.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-333.md").read_text()

start = file_flt.index("_FX NTSTATUS File_CheckFileObject(")
end = file_flt.index("// continue with normal processing", start)
block = file_flt[start:end]

for term in [
    "SREV-333: Kaspersky 2014 queues an APC into Wow64 processes",
    "NtSetInformationThread",
    "Gui_ConnectToWindowStationAndDesktop",
    "SREV-333: keep this x64 pre-SbieDll-loaded swmon_*_kl1 sentinel narrow.",
    "#ifdef _WIN64",
    "if (! proc->sbiedll_loaded)",
    "WCHAR *Backslash = wcsrchr(NameString->Buffer, L'\\\\');",
    "WCHAR *Underscore = wcsrchr(NameString->Buffer, L'_');",
    "_wcsicmp(Underscore, L\"_kl1\") == 0",
    "_wcsnicmp(Backslash, L\"\\\\swmon_\", 7) == 0",
    "return STATUS_BAD_INITIAL_PC;",
]:
    require(block, term, "file_flt Kaspersky sentinel")

for stale in [
    "hack for Kaspersky 2014",
    "$Workaround$ - 3rd party fix",
]:
    reject(block, stale, "Kaspersky sentinel comment")

open_start = syscall_open.index("_FX NTSTATUS Syscall_OpenHandle(")
open_end = syscall_open.index("//---------------------------------------------------------------------------\n// Syscall_GetNextProcess", open_start)
open_block = syscall_open[open_start:open_end]
for term in [
    "if (status == STATUS_BAD_INITIAL_PC)",
    "special status for immediate return;",
    "return status;",
]:
    require(open_block, term, "Syscall_OpenHandle sentinel handling")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "SREV-329",
    "NtSetInformationThread pass-through guard",
    "Gui_ConnectToWindowStationAndDesktop",
]:
    require(spec, term, "SREV-329 adjacency")

for term in [
    "### SREV-333: File Filter Kaspersky Swmon Sentinel",
    "FILE_FLT_KASPERSKY_SWMON_SENTINEL",
    "srev-333-file-flt-kaspersky-swmon-sentinel.schema.json",
    "Sandboxie/core/drv/file_flt.c",
    "STATUS_BAD_INITIAL_PC",
    "swmon_*_kl1",
    "SREV-329",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-333 source gate passed")
