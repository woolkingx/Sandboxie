#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-107 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-107 failed: {label} still contains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-107-driverassist-host-inject-restart-coalescing.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-107 failed: schema is not draft-07")
if schema.get("id") != "DRIVERASSIST_HOST_INJECT_RESTART_COALESCING":
    raise SystemExit("SREV-107 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "each config update increments a generation counter",
    "only one restart worker may be active at a time",
    "250ms quiet window",
    "must not hold m_critSecHostInjectedSvcs while sleeping",
    "SCM enumeration stop and start work runs under m_critSecHostInjectedSvcs",
    "new generation appears while SCM work is running",
    "another worker claims the new generation",
    "EnumServicesStatusExW enumerates services",
    "ControlService sends service control codes",
    "StartServiceW starts services",
    "must not change HostInjectProcess matching",
]:
    require(contracts, term, "schema")

source = (ROOT / "Sandboxie/core/svc/DriverAssist.cpp").read_text()
host = (ROOT / "Sandboxie/core/svc/HostInjectProcessUtil.cpp").read_text()
driver_conf = (ROOT / "Sandboxie/core/drv/conf.c").read_text()
api_defs = (ROOT / "Sandboxie/core/drv/api_defs.h").read_text()
spec = (ROOT / "docs/plan/srev-107-driverassist-host-inject-restart-coalescing.md").read_text()
ledger = read_combined_ledger(ROOT)

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "else if (msgid == SVC_CONFIG_UPDATED)",
    "SbieIniServer::NotifyConfigReloaded();",
    "SbieDll_InjectLow_InitSyscalls(TRUE);",
    "RestartHostInjectedSvcs();",
    "static volatile LONG RestartGeneration = 0;",
    "static volatile LONG RestartWorkerActive = 0;",
    "InterlockedIncrement(&RestartGeneration);",
    "InterlockedCompareExchange(&RestartWorkerActive, 1, 0)",
    "LONG processedGeneration = 0;",
    "observedGeneration = InterlockedCompareExchange(&RestartGeneration, 0, 0);",
    "Sleep(250);",
    "observedGeneration != InterlockedCompareExchange(&RestartGeneration, 0, 0)",
    "EnterCriticalSection(&m_critSecHostInjectedSvcs);",
    "::RestartHostInjectedSvcs();",
    "LeaveCriticalSection(&m_critSecHostInjectedSvcs);",
    "processedGeneration = observedGeneration;",
    "InterlockedExchange(&RestartWorkerActive, 0);",
    "InterlockedCompareExchange(&RestartGeneration, 0, 0) == processedGeneration",
]:
    require(source, term, "DriverAssist.cpp source shape")

function_start = source.index("void DriverAssist::RestartHostInjectedSvcs()")
function_end = source.index("//---------------------------------------------------------------------------", function_start)
function = source[function_start:function_end]

sleep = function.index("Sleep(250);")
enter = function.index("EnterCriticalSection(&m_critSecHostInjectedSvcs);")
call = function.index("::RestartHostInjectedSvcs();")
leave = function.index("LeaveCriticalSection(&m_critSecHostInjectedSvcs);")
release = function.index("InterlockedExchange(&RestartWorkerActive, 0);")
if not (sleep < enter < call < leave < release):
    raise SystemExit("SREV-107 failed: quiet-window and SCM critical-section order is wrong")

for stale in [
    "resulting in this function getting triggered way to often",
    "hence we implement a small workaround",
    "JobCounter",
    "calls go in and waits until the last one",
]:
    reject(function, stale, "RestartHostInjectedSvcs")

for term in [
    "Api_SendServiceMessage(SVC_CONFIG_UPDATED",
    "process_id",
]:
    require(driver_conf, term, "driver config update shape")

for term in [
    "SVC_CONFIG_UPDATED",
    "SVC_INJECT_PROCESS",
]:
    require(api_defs, term, "api_defs service message shape")

for term in [
    "void BuildSvcSet()",
    "HostInjectProcess",
    "BOOL IsSvcInjected(DWORD dwPid)",
    "OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ",
    "void RestartService(SC_HANDLE hScm, WCHAR *wszServiceName)",
    "OpenService(hScm, wszServiceName, SERVICE_ALL_ACCESS)",
    "ControlService(hService, SERVICE_CONTROL_STOP",
    "StartServiceW(hService, 0, NULL)",
    "void RestartHostInjectedSvcs()",
    "OpenSCManagerW(NULL, SERVICES_ACTIVE_DATABASE, SC_MANAGER_ALL_ACCESS)",
    "EnumServicesStatusExW(hScm, SC_ENUM_PROCESS_INFO, SERVICE_WIN32, SERVICE_ACTIVE",
    "_wcsicmp(pService->lpServiceName, SBIESVC)",
    "g_setSvcNames.find(pService->lpServiceName)",
]:
    require(host, term, "HostInjectProcessUtil.cpp policy preservation")

for term in [
    "### SREV-107: DriverAssist Host Inject Restart Coalescing",
    "DRIVERASSIST_HOST_INJECT_RESTART_COALESCING",
    "srev-107-driverassist-host-inject-restart-coalescing.schema.json",
    "RestartGeneration",
    "RestartWorkerActive",
    "Sandboxie/core/svc/DriverAssist.cpp",
]:
    require(ledger, term, "ledger")

print("SREV-107 schema/source gate passed")
