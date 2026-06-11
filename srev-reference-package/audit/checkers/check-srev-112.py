#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-112 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-112 failed: {label} still contains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-112-comserver-slave-ipc-open-lifetime.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-112 failed: schema is not draft-07")
if schema.get("id") != "COMSERVER_SLAVE_IPC_OPEN_LIFETIME":
    raise SystemExit("SREV-112 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "bounded parent-generated proxy command line",
    "colon separator",
    "parent-created mutex request event reply event and file mapping",
    "Event1 is the request event",
    "Event2 is the reply event",
    "closed on startup failure",
    "unmapped on startup failure",
    "CoInitializeEx must succeed",
    "CoUninitialize",
    "must not change object names access masks COM request dispatch",
]:
    require(contracts, term, "schema")

source = (ROOT / "Sandboxie/core/svc/comserver.cpp").read_text()
spec = (ROOT / "docs/plan/srev-112-comserver-slave-ipc-open-lifetime.md").read_text()
ledger = read_combined_ledger(ROOT)

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

start = source.index("void ComServer::RunSlave(")
end = source.index("// FindSlaveObject", start)
run_slave = source[start:end]

for term in [
    "HANDLE hParentProcessMutex = NULL;",
    "HANDLE hEvent1 = NULL;",
    "HANDLE hEvent2 = NULL;",
    "HANDLE hMap = NULL;",
    "COM_SLAVE_MAP *pMap = NULL;",
    "HRESULT hrCoInit = E_FAIL;",
    "WCHAR *colon = wcsrchr(objname, L':');",
    "if (! colon)",
    "goto finish;",
    "OpenMutex(MUTEX_MODIFY_STATE | SYNCHRONIZE, FALSE, objname);",
    "hEvent1 = OpenEvent(EVENT_MODIFY_STATE | SYNCHRONIZE, FALSE, objname);",
    "hEvent2 = OpenEvent(EVENT_MODIFY_STATE | SYNCHRONIZE, FALSE, objname);",
    "if (! hEvent2)",
    "hMap = OpenFileMapping(FILE_MAP_ALL_ACCESS, FALSE, objname);",
    "MapViewOfFile(hMap, FILE_MAP_ALL_ACCESS, 0, 0, COM_SLAVE_MAP_SIZE);",
    "hrCoInit = CoInitializeEx(NULL, COINIT_APARTMENTTHREADED);",
    "if (FAILED(hrCoInit))",
    "CoInitializeSecurity(",
    "SetEvent(hEvent2);",
    "finish:",
    "if (SUCCEEDED(hrCoInit))",
    "CoUninitialize();",
    "HeapDestroy(m_heap);",
    "UnmapViewOfFile(pMap);",
    "CloseHandle(hMap);",
    "CloseHandle(hEvent2);",
    "CloseHandle(hEvent1);",
    "CloseHandle(hParentProcessMutex);",
]:
    require(run_slave, term, "RunSlave topology")

reject(run_slave, "if (! hEvent1)\n        return;", "stale Event2 check")
reject(run_slave, "HANDLE hEvent2 =\n                OpenEvent", "old scoped hEvent2 declaration")
reject(run_slave, "if (! hMap)\n        return;", "old unpaired hMap return")
reject(run_slave, "if (! pMap)\n        return;", "old unpaired map return")
reject(run_slave, "CoInitializeEx(NULL, COINIT_APARTMENTTHREADED);\n\n    CoInitializeSecurity", "unchecked CoInitializeEx")

for term in [
    "if (rc != STATUS_WAIT_1 || pMap->msgid == -1)",
    "ExitProcess(0);",
    "WaitForMultipleObjects(2, handles, FALSE, INFINITE);",
    "GetClassObjectSlave(pMap, &ObjectsList, &exc, &hr);",
    "SetEvent(hEvent2);",
]:
    require(run_slave, term, "preserved steady-state dispatch")

for term in [
    "### SREV-112: ComServer Slave IPC Open Lifetime",
    "COMSERVER_SLAVE_IPC_OPEN_LIFETIME",
    "srev-112-comserver-slave-ipc-open-lifetime.schema.json",
    "Sandboxie/core/svc/comserver.cpp",
    "ComServer::RunSlave",
    "OpenEvent",
    "MapViewOfFile",
    "CoInitializeEx",
]:
    require(ledger, term, "ledger")

print("SREV-112 schema/source gate passed")
