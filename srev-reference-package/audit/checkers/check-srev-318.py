#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-318 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-318 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-318-ldr-ntterminateprocess-disabled-hook-boundary.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-318 failed: schema is not draft-07")
if schema.get("id") != "LDR_NTTERMINATEPROCESS_DISABLED_HOOK_BOUNDARY":
    raise SystemExit("SREV-318 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/dll/ldr.c":
    raise SystemExit("SREV-318 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "LdrRegisterDllNotification returns a callback identifier cookie used for unregister",
    "LdrUnregisterDllNotification owns cancellation of the registered DLL notification cookie",
    "LdrDllNotification callback context is constrained",
    "TerminateProcess is unconditional process termination",
    "the NtTerminateProcess hook remains disabled until ARM64 process-exit runtime proof exists",
    "comments and proof only",
]:
    require(contracts, term, "schema")

ldr = (ROOT / "Sandboxie/core/dll/ldr.c").read_text()
spec = (ROOT / "docs/plan/srev-318-ldr-ntterminateprocess-disabled-hook-boundary.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-318.md").read_text()
srev_312 = (ROOT / "docs/plan/ledger/srev-312.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "//static P_NtTerminateProcess     __sys_NtTerminateProcess = NULL;",
    "//NTSTATUS Ldr_NtTerminateProcess(HANDLE  ProcessHandle, NTSTATUS ExitStatus)",
    "//        __sys_LdrUnregisterDllNotification(LdrLoaderCookie);",
    "//    rc = __sys_NtTerminateProcess(ProcessHandle, ExitStatus);",
]:
    require(ldr, term, "inactive NtTerminateProcess body")

init_start = ldr.index("_FX BOOLEAN Ldr_Init()")
init_end = ldr.index("else { // Windows 8 and before", init_start)
init = ldr[init_start:init_end]
for term in [
    "__sys_LdrRegisterDllNotification = (P_LdrRegisterDllNotification)GetProcAddress(Dll_Ntdll, \"LdrRegisterDllNotification\");",
    "__sys_LdrUnregisterDllNotification = (P_LdrUnregisterDllNotification)GetProcAddress(Dll_Ntdll, \"LdrUnregisterDllNotification\");",
    "rc = __sys_LdrRegisterDllNotification(0, ((void *)Ldr_LdrDllNotification), NULL, &LdrLoaderCookie);",
    "if (rc) {\n            return FALSE;\n        }",
    "SREV-318: NtTerminateProcess notification-cookie cleanup remains",
    "disabled; enabling it needs ARM64 process-exit runtime proof.",
    "//SBIEDLL_HOOK(Ldr_, NtTerminateProcess);",
    "SBIEDLL_HOOK(Ldr_Win10_, LdrLoadDll);",
]:
    require(init, term, "Ldr_Init Windows 8.1+ block")
for stale in [
    "Todo: Fix-Me",
    "this hangs some processes on arm64",
]:
    reject(init, stale, "Ldr_Init NtTerminateProcess comment")

for term in [
    "LDR_DLL_NOTIFICATION_LOCK_UNION_GATE",
    "Ldr_LdrDllNotification",
    "Windows 8.1+ DLL load/unload smoke plus ARM64/ARM64EC",
]:
    require(srev_312, term, "SREV-312 adjacency")
    require(spec, term, "spec adjacency")

for term in [
    "LDR_NTTERMINATEPROCESS_DISABLED_HOOK_BOUNDARY",
    "disabled topology is not active source behavior today",
    "No `LdrRegisterDllNotification`",
    "Runtime gate: Windows ARM64/ARM64EC process-exit matrix",
]:
    require(spec, term, "spec")

for term in [
    "### SREV-318: Ldr NtTerminateProcess Disabled Hook Boundary",
    "LDR_NTTERMINATEPROCESS_DISABLED_HOOK_BOUNDARY",
    "srev-318-ldr-ntterminateprocess-disabled-hook-boundary.schema.json",
    "Sandboxie/core/dll/ldr.c",
    "Ldr_Init",
    "LdrLoaderCookie",
    "NtTerminateProcess",
    "SREV-312",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-318 source gate passed")
