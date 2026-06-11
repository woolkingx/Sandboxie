#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-101 failed: {label} missing {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-101-syscall-disabled-skip-and-procmon-guard.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-101 failed: schema is not draft-07")
if schema.get("id") != "SYSCALL_DISABLED_SKIP_AND_PROCMON_GUARD":
    raise SystemExit("SREV-101 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "enumerates NTDLL Zw exports",
    "YieldExecution and MapViewOfSection compatibility skip branches are intentionally inactive",
    "must not be described as active third-party workaround policy",
    "MapViewOfSection hook policy must not be changed",
    "QuerySystemInformation is registered through Syscall_Set3",
    "SystemInformationClass 0xb9 is a private runtime guard value",
    "NtQuerySystemInformation is a variable native API surface",
    "does not change syscall hook registration, skip behavior, or QuerySystemInformation return policy",
]:
    require(contracts, term, "schema")

syscall = (ROOT / "Sandboxie/core/drv/syscall.c").read_text()
spec = (ROOT / "docs/plan/srev-101-syscall-disabled-skip-and-procmon-guard.md").read_text()
ledger = read_combined_ledger(ROOT)

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "Dll_Load(Dll_NTDLL)",
    "Dll_GetNextProc(dll, \"Zw\", &name, &proc_index)",
    "Syscall_GetIndexFromNtdll(ntdll_code)",
    "Syscall_GetKernelAddr(",
    "List_Insert_After(&Syscall_List, NULL, entry)",
    "Syscall_Set3(\"QuerySystemInformation\", Syscall_QuerySystemInfo_SupportProcmonStack)",
    "Historical disabled skip: McAfee used YieldExecution stack data",
    "//if (    IS_PROC_NAME(14, \"YieldExecution\"))",
    "Historical disabled skip: Chrome wow_helper compatibility remains",
    "//if (    IS_PROC_NAME(16,  \"MapViewOfSection\"))",
    "user_args[0] == 0xb9",
    "bRet = FALSE;",
    "destabilize x64 context",
]:
    require(syscall, term, "syscall.c source shape")

for stale in [
    "$Workaround$ - 3rd party fix",
    "can still crash a x64 one",
]:
    if stale in syscall:
        raise SystemExit(f"SREV-101 failed: stale wording remains {stale!r}")

for term in [
    "NtQuerySystemInformation",
    "altered or unavailable",
    "ZwMapViewOfSection",
    "private runtime-version-specific value",
    "intentionally inactive",
    "No syscall hook registration",
]:
    require(spec, term, "spec shape")

for term in [
    "### SREV-101: Syscall Disabled Skip And Procmon Guard",
    "SYSCALL_DISABLED_SKIP_AND_PROCMON_GUARD",
    "srev-101-syscall-disabled-skip-and-procmon-guard.schema.json",
]:
    require(ledger, term, "ledger")

print("SREV-101 schema/source gate passed")
