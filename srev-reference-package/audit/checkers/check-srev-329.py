#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-329 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-329 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-329-sxs-ntsetinformationthread-pass-through-hook.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-329 failed: schema is not draft-07")
if schema.get("id") != "SXS_NTSETINFORMATIONTHREAD_PASS_THROUGH_HOOK":
    raise SystemExit("SREV-329 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/dll/sxs.c":
    raise SystemExit("SREV-329 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "NtSetInformationThread owns the thread-information transition",
    "must preserve arguments and return the native NTSTATUS",
    "hook changes call topology",
    "adjacent change-notify-token evidence",
    "removing the hook requires Windows browser/runtime proof",
    "changes comments and proof only",
]:
    require(contracts, term, "schema contracts")

sxs = (ROOT / "Sandboxie/core/dll/sxs.c").read_text()
gui = (ROOT / "Sandboxie/core/dll/gui.c").read_text()
thread_token = (ROOT / "Sandboxie/core/drv/thread_token.c").read_text()
spec = (ROOT / "docs/plan/srev-329-sxs-ntsetinformationthread-pass-through-hook.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-329.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

wrapper_start = sxs.index("_FX NTSTATUS Sxs_NtSetInformationThread(")
wrapper_end = sxs.index("// Sxs_NtCreateTransaction", wrapper_start)
wrapper = sxs[wrapper_start:wrapper_end]

init_start = sxs.index("_FX BOOLEAN Sxs_InitKernel32(")
init_end = sxs.index("// place ntdll.dll hooks only if TrustedInstaller", init_start)
init_func = sxs[init_start:init_end]

for term in [
    "HANDLE          ThreadHandle",
    "THREADINFOCLASS ThreadInformationClass",
    "PVOID           ThreadInformation",
    "ULONG           ThreadInformationLength",
    "return __sys_NtSetInformationThread(ThreadHandle,\n        ThreadInformationClass,\n        ThreadInformation,\n        ThreadInformationLength);",
]:
    require(wrapper, term, "Sxs_NtSetInformationThread source")

for term in [
    "SREV-329: keep this narrow NtSetInformationThread pass-through hook",
    "third-party NTAPI-stub guard",
    "change-notify-token path referenced",
    "Removing it needs Windows",
    "browser matrix proof",
    "GetProcAddress(Dll_Ntdll, \"NtSetInformationThread\")",
    "SBIEDLL_HOOK(Sxs_, NtSetInformationThread);",
]:
    require(init_func, term, "Sxs_InitKernel32 source")

for stale in [
    "Opera hooks NtSetInformationThread",
    "Tested with opera 117",
    "this workaround seems no longer required",
]:
    reject(init_func, stale, "SXS NtSetInformationThread comment")

for term in [
    "Thread_SetInformationThread_ChangeNotifyToken",
    "if (__sys_NtSetInformationThread)",
    "rc = __sys_NtSetInformationThread(NtCurrentThread(),",
    "rc = NtSetInformationThread(NtCurrentThread(),",
]:
    require(gui, term, "GUI change-notify-token path")

for term in [
    "Thread_SetInformationThread_ChangeNotifyToken",
    "syscall handler for NtSetInformationThread",
    "ThreadImpersonationToken",
]:
    require(thread_token, term, "driver change-notify-token path")

for term in [
    "SXS_NTSETINFORMATIONTHREAD_PASS_THROUGH_HOOK",
    "No `GetProcAddress`, `SBIEDLL_HOOK`, wrapper function signature",
    "Windows gate: browser/runtime matrix",
    "hook remains active",
]:
    require(spec, term, "spec")

for term in [
    "kind: srev-ledger-entry",
    "id: SREV-329",
    "owner: Sandboxie/core/dll/sxs.c",
    "spec: docs/plan/srev-329-sxs-ntsetinformationthread-pass-through-hook.md",
    "schema: docs/plan/srev-329-sxs-ntsetinformationthread-pass-through-hook.schema.json",
    "checker: docs/plan/check-srev-329.py",
]:
    require(ledger_fragment, term, "ledger fragment header")

for term in [
    "### SREV-329: SXS NtSetInformationThread Pass-Through Hook",
    "SXS_NTSETINFORMATIONTHREAD_PASS_THROUGH_HOOK",
    "Sxs_NtSetInformationThread",
    "Thread_SetInformationThread_ChangeNotifyToken",
]:
    require(ledger, term, "combined ledger")

print("SREV-329 schema/source gate passed")
