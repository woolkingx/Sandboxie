#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-140 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-140 failed: {label} still contains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-140-hostinject-service-restart-state.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-140 failed: schema is not draft-07")
if schema.get("id") != "HOSTINJECT_SERVICE_RESTART_STATE":
    raise SystemExit("SREV-140 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "HostInjectProcessUtil.cpp owns only the executor edge enumerate active services compare policy to module-injection state then restart mismatches",
    "BuildSvcSet and IsSvcInjected policy matching remain unchanged",
    "A restart stop edge is complete only when QueryServiceStatusEx reports SERVICE_STOPPED or the service was already inactive",
    "StartServiceW may run only after the stop edge is complete",
    "If stop fails for a reason other than already-inactive or stop-pending state the executor must not issue a blind start against the still-running service",
    "Stop-pending state may be waited through QueryServiceStatusEx",
    "The service enumeration buffer allocated with new BYTE[] must be released with delete[]",
]:
    require(contracts, term, "schema")

source = (ROOT / "Sandboxie/core/svc/HostInjectProcessUtil.cpp").read_text()
driver = (ROOT / "Sandboxie/core/svc/DriverAssist.cpp").read_text()
srev107 = (ROOT / "docs/plan/srev-107-driverassist-host-inject-restart-coalescing.md").read_text()
spec = (ROOT / "docs/plan/srev-140-hostinject-service-restart-state.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-140.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "RestartGeneration",
    "RestartWorkerActive",
    "::RestartHostInjectedSvcs();",
]:
    require(driver, term, "SREV-107 coalescing owner")

for term in [
    "the wrapper must not change BuildSvcSet, IsSvcInjected, RestartService, or HostInjectProcess matching policy",
    "SCM enumeration / stop / start work runs under m_critSecHostInjectedSvcs",
]:
    require(srev107, term, "SREV-107 boundary")

for term in [
    "BOOL WaitForServiceState(SC_HANDLE hService, DWORD dwDesiredState, DWORD dwTimeout)",
    "SERVICE_STATUS_PROCESS stServiceStatus;",
    "QueryServiceStatusEx(hService, SC_STATUS_PROCESS_INFO, (LPBYTE)&stServiceStatus,",
    "sizeof(stServiceStatus), &dwBytesNeeded)",
    "stServiceStatus.dwCurrentState == dwDesiredState",
    "stServiceStatus.dwWaitHint / 10",
    "dwWait < 100",
    "dwWait > 1000",
    "Sleep(dwWait);",
    "return FALSE;",
]:
    require(source, term, "WaitForServiceState")

for term in [
    "void BuildSvcSet()",
    "HostInjectProcess",
    "SbieApi_QueryConf(wszConfigLine, L\"HostInjectProcess\", 0, wszConfigLine, sizeof(wszConfigLine))",
    "swscanf(wszConfigLine, L\"%260[^'|']|%260s\", wszProcName, wszSvcName)",
    "g_setSvcNames.insert(wstring(wszSvcName));",
    "BOOL IsSvcInjected(DWORD dwPid)",
    "OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, FALSE, dwPid)",
    "EnumProcessModules(hProcess, hMods, sizeof(hMods), &dwSize)",
    "GetModuleBaseNameW(hProcess, hMods[n], wszModName, sizeof(wszModName) / sizeof(WCHAR))",
    "_wcsicmp(wszModName, SBIEDLL L\".dll\") == 0",
]:
    require(source, term, "HostInject matching preservation")

restart = source[
    source.index("void RestartService"):
    source.index("void RestartHostInjectedSvcs")
]
for term in [
    "BOOL canStart = TRUE;",
    "OpenService(hScm, wszServiceName, SERVICE_ALL_ACCESS)",
    "ControlService(hService, SERVICE_CONTROL_STOP, &stServiceStatus)",
    "canStart = WaitForServiceState(hService, SERVICE_STOPPED, 30000);",
    "dwError == ERROR_SERVICE_NOT_ACTIVE",
    "dwError == ERROR_SERVICE_CANNOT_ACCEPT_CTRL",
    "canStart = FALSE;",
    "if (canStart)\n            res = StartServiceW(hService, 0, NULL);",
    "CloseServiceHandle(hService);",
]:
    require(restart, term, "RestartService")

if restart.index("ControlService(hService, SERVICE_CONTROL_STOP") > restart.index("StartServiceW(hService, 0, NULL)"):
    raise SystemExit("SREV-140 failed: StartServiceW appears before stop request")
if restart.index("WaitForServiceState(hService, SERVICE_STOPPED, 30000)") > restart.index("StartServiceW(hService, 0, NULL)"):
    raise SystemExit("SREV-140 failed: StartServiceW appears before SERVICE_STOPPED wait")

for term in [
    "OpenSCManagerW(NULL, SERVICES_ACTIVE_DATABASE, SC_MANAGER_ALL_ACCESS)",
    "LPBYTE pProcBuf = new BYTE[dwProcBufSize];",
    "EnumServicesStatusExW(hScm, SC_ENUM_PROCESS_INFO, SERVICE_WIN32, SERVICE_ACTIVE",
    "_wcsicmp(pService->lpServiceName, SBIESVC)",
    "g_setSvcNames.find(pService->lpServiceName)",
    "RestartService(hScm, pService->lpServiceName);",
    "delete[] pProcBuf;",
]:
    require(source, term, "RestartHostInjectedSvcs")

reject(source, "delete pProcBuf;", "service enumeration buffer owner")

for term in [
    "### SREV-140: HostInject Service Restart State",
    "HOSTINJECT_SERVICE_RESTART_STATE",
    "srev-140-hostinject-service-restart-state.schema.json",
    "WaitForServiceState",
    "delete[] pProcBuf",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-140 schema/source gate passed")
