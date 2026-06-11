#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-130 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-130 failed: {label} still contains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-130-driverassist-inject-process-handle-state.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-130 failed: schema is not draft-07")
if schema.get("id") != "DRIVERASSIST_INJECT_PROCESS_HANDLE_STATE":
    raise SystemExit("SREV-130 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "InjectLow owns a process handle state variable initialized to NULL before any finish edge",
    "InjectLow_OpenProcess returns a real process handle only after OpenProcess succeeds and creation time matches",
    "OpenProcess failure and creation-time mismatch leave InjectLow hProcess NULL",
    "finish cleanup tests only the initialized hProcess state before API_INJECT_COMPLETE failure notification and CloseHandle",
    "CloseHandle is called only for a non-null process handle produced by InjectLow_OpenProcess",
    "driver-not-ready early exit does not read an uninitialized process handle",
    "successful injection GuiServer MountManager and API_INJECT_COMPLETE topology are unchanged",
]:
    require(contracts, term, "schema")

source = (ROOT / "Sandboxie/core/svc/DriverAssistInject.cpp").read_text()
spec = (ROOT / "docs/plan/srev-130-driverassist-inject-process-handle-state.md").read_text()
ledger = read_combined_ledger(ROOT)

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

inject = source[
    source.index("void DriverAssist::InjectLow(void *_msg)"):
    source.index("// InjectLow_OpenProcess")
]
open_process = source[
    source.index("HANDLE DriverAssist::InjectLow_OpenProcess"):
]

for term in [
    "WCHAR* file_root_path = NULL;",
    "WCHAR* reg_root_path = NULL;",
    "HANDLE hProcess = NULL;",
    "if (!m_DriverReady) {",
    "errlvl = 0xFF;\n\t\tgoto finish;",
    "hProcess = InjectLow_OpenProcess(_msg);",
    "if (!hProcess) {",
    "errlvl = SbieDll_InjectLow(hProcess, sbieLow.init_flags, TRUE);",
    "GuiServer::GetInstance()->InitProcess(",
    "MountManager::GetInstance()->AcquireBoxRoot(",
    "status = SbieApi_Call(API_INJECT_COMPLETE, 2, (ULONG_PTR)msg->process_id, SandboxieLogonSid);",
    "status = SbieApi_Call(API_INJECT_COMPLETE, 1, (ULONG_PTR)msg->process_id);",
    "if (hProcess) {",
    "SbieApi_Call(API_INJECT_COMPLETE, 3, (ULONG_PTR)msg->process_id, NULL, errlvl);",
    "CloseHandle(hProcess);",
]:
    require(inject, term, "InjectLow")

if inject.index("HANDLE hProcess = NULL;") > inject.index("if (!m_DriverReady)"):
    raise SystemExit("SREV-130 failed: hProcess initialization is after early finish edge")
if inject.index("HANDLE hProcess = NULL;") > inject.index("finish:"):
    raise SystemExit("SREV-130 failed: hProcess initialization is after finish label")
reject(inject, "HANDLE hProcess = InjectLow_OpenProcess(_msg);", "stale declaration-at-open pattern")

for term in [
    "const ULONG _DesiredAccess =",
    "PROCESS_QUERY_INFORMATION",
    "HANDLE hProcess = OpenProcess(_DesiredAccess, FALSE, msg->process_id);",
    "BOOL ok = GetProcessTimes(hProcess, &time, &time1, &time2, &time3);",
    "if (ok && *(ULONG64 *)&time.dwLowDateTime == msg->create_time) {",
    "return hProcess;",
    "CloseHandle(hProcess);",
    "return NULL;",
]:
    require(open_process, term, "InjectLow_OpenProcess")

if open_process.index("CloseHandle(hProcess);") > open_process.index("return NULL;"):
    raise SystemExit("SREV-130 failed: mismatch path no longer closes before NULL return")

for term in [
    "### SREV-130: DriverAssist InjectLow Process Handle State",
    "DRIVERASSIST_INJECT_PROCESS_HANDLE_STATE",
    "srev-130-driverassist-inject-process-handle-state.schema.json",
    "Sandboxie/core/svc/DriverAssistInject.cpp",
    "DriverAssist::InjectLow",
    "DriverAssist::InjectLow_OpenProcess",
    "OpenProcess",
    "GetProcessTimes",
    "CloseHandle",
    "API_INJECT_COMPLETE",
    "hProcess",
]:
    require(ledger, term, "ledger")

print("SREV-130 schema/source gate passed")
