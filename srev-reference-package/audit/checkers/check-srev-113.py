#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-113 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-113 failed: {label} still contains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-113-service-entry-resource-lifetime.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-113 failed: schema is not draft-07")
if schema.get("id") != "SERVICE_ENTRY_RESOURCE_LIFETIME":
    raise SystemExit("SREV-113 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "WinMain owns process-wide initialization",
    "process-local critical section",
    "every local return path from WinMain after SID cache initialization",
    "proxy command-line detection order",
    "StartServiceCtrlDispatcher remains the SCM boundary",
    "failed StartServiceCtrlDispatcher preserves GetLastError",
    "InitializeEventLog owns the event-log handle",
    "CloseEventLog on service initialization failure and STOP SHUTDOWN cleanup",
]:
    require(contracts, term, "schema")

source = (ROOT / "Sandboxie/core/svc/main.cpp").read_text()
spec = (ROOT / "docs/plan/srev-113-service-entry-resource-lifetime.md").read_text()
ledger = read_combined_ledger(ROOT)

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

start = source.index("int WinMain(")
end = source.index("// ServiceMain", start)
winmain = source[start:end]

for term in [
    "DriverAssist::InitializeSidCache();",
    "int rc = NO_ERROR;",
    "WCHAR *cmdline2 = wcsstr(cmdline, SANDBOXIE L\"_ComProxy\");",
    "ComServer::RunSlave(cmdline2);",
    "WCHAR *cmdline3 = wcsstr(cmdline, SANDBOXIE L\"_UacProxy\");",
    "ServiceServer::RunUacSlave(cmdline3);",
    "WCHAR *cmdline4 = wcsstr(cmdline, SANDBOXIE L\"_NetProxy\");",
    "NetApiServer::RunSlave(cmdline4);",
    "WCHAR *cmdline5 = wcsstr(cmdline, SANDBOXIE L\"_GuiProxy\");",
    "GuiServer::RunSlave(cmdline5);",
    "WCHAR *cmdline6 = wcsstr(cmdline, SANDBOXIE L\"_UserProxy\");",
    "UserServer::RunWorker(cmdline6);",
    "goto finish;",
    "if (! StartServiceCtrlDispatcher(myServiceTable))",
    "rc = GetLastError();",
    "finish:",
    "DriverAssist::DestroySidCache();",
    "return rc;",
]:
    require(winmain, term, "WinMain topology")

for old_return in [
    "ComServer::RunSlave(cmdline2);\n            return NO_ERROR;",
    "ServiceServer::RunUacSlave(cmdline3);\n            return NO_ERROR;",
    "NetApiServer::RunSlave(cmdline4);\n            return NO_ERROR;",
    "GuiServer::RunSlave(cmdline5);\n            return NO_ERROR;",
    "UserServer::RunWorker(cmdline6);\n            return NO_ERROR;",
    "return GetLastError();",
]:
    reject(winmain, old_return, "old unpaired WinMain return")

service_start = source.index(
    "void WINAPI ServiceMain(",
    source.index("// ServiceMain"),
)
handler_start = source.index("DWORD WINAPI ServiceHandlerEx(", service_start)
service_main = source[service_start:handler_start]
handler = source[handler_start:source.index("// LogEvent", handler_start)]

for term in [
    "EventLog = OpenEventLog(NULL, ServiceName);",
    "if (EventLog) {",
    "CloseEventLog(EventLog);",
    "EventLog = NULL;",
    "ServiceStatus.dwCurrentState        = SERVICE_STOPPED;",
    "ServiceStatus.dwWin32ExitCode       = ERROR_SERVICE_SPECIFIC_ERROR;",
    "SetServiceStatus(ServiceStatusHandle, &ServiceStatus);",
]:
    require(service_main, term, "ServiceMain event-log cleanup")

for term in [
    "if (dwControl == SERVICE_CONTROL_STOP ||",
    "delete pipeServer;",
    "DriverAssist::Shutdown();",
    "MountManager::Shutdown();",
    "if (EventLog) {",
    "CloseEventLog(EventLog);",
    "EventLog = NULL;",
    "SetServiceStatus(ServiceStatusHandle, &ServiceStatus)",
]:
    require(handler, term, "ServiceHandlerEx cleanup")

for term in [
    "### SREV-113: Service Entry Resource Lifetime",
    "SERVICE_ENTRY_RESOURCE_LIFETIME",
    "srev-113-service-entry-resource-lifetime.schema.json",
    "Sandboxie/core/svc/main.cpp",
    "DriverAssist::InitializeSidCache",
    "DriverAssist::DestroySidCache",
    "StartServiceCtrlDispatcher",
    "OpenEventLog",
    "CloseEventLog",
]:
    require(ledger, term, "ledger")

print("SREV-113 schema/source gate passed")
