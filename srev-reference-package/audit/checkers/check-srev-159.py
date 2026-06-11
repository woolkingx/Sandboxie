#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-159 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-159 failed: {label} still contains {needle!r}")


def section(text: str, start: str, end: str) -> str:
    start_index = text.index(start)
    end_index = text.index(end, start_index)
    return text[start_index:end_index]


schema = json.loads(
    (ROOT / "docs/plan/srev-159-pipeserver-thread-vector-lifetime.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-159 failed: schema is not draft-07")
if schema.get("id") != "PIPESERVER_THREAD_VECTOR_LIFETIME":
    raise SystemExit("SREV-159 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "PipeServer owns a thread handle vector allocated from GetProcessHeap",
    "Start must not create the server port or index m_Threads when the vector allocation failed",
    "m_ThreadCount is the number of valid thread handles",
    "waits termination close and cleanup may operate only on m_ThreadCount valid handles",
    "every successful CreateThread handle is eventually closed with CloseHandle",
    "startup failure after partial thread creation shuts down the published port",
    "the HeapAlloc vector is freed with HeapFree in the destructor",
    "does not change LPC message framing request dispatch target registration impersonation or server-port security descriptor policy",
    "Linux source gate is not Windows runtime proof",
]:
    require(contracts, term, "schema")

header = (ROOT / "Sandboxie/core/svc/PipeServer.h").read_text()
source = (ROOT / "Sandboxie/core/svc/PipeServer.cpp").read_text()
spec = (ROOT / "docs/plan/srev-159-pipeserver-thread-vector-lifetime.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-159.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "void ShutdownPortAndThreads();",
    "volatile HANDLE m_hServerPort;",
    "HANDLE *m_Threads;",
    "ULONG m_ThreadCount;",
]:
    require(header, term, "PipeServer.h")

ctor = section(source, "PipeServer::PipeServer()", "//---------------------------------------------------------------------------\n// Initializator")
for term in [
    "m_hServerPort = NULL;",
    "m_ThreadCount = 0;",
    "m_Threads = (HANDLE *)HeapAlloc(GetProcessHeap(), 0, len_threads);",
    "if (m_Threads)\n        memzero(m_Threads, len_threads);",
]:
    require(ctor, term, "constructor")

dtor = section(source, "PipeServer::~PipeServer()", "//---------------------------------------------------------------------------\n// Register")
for term in [
    "ShutdownPortAndThreads();",
    "if (m_Threads) {",
    "HeapFree(GetProcessHeap(), 0, m_Threads);",
    "m_Threads = NULL;",
    "Pool_Delete(m_pool);",
    "DeleteCriticalSection(&m_lock);",
]:
    require(dtor, term, "destructor")
reject(dtor, "WaitForMultipleObjects(\n                                NUMBER_OF_THREADS, m_Threads", "destructor full-vector wait")

shutdown = section(source, "void PipeServer::ShutdownPortAndThreads()", "//---------------------------------------------------------------------------\n// Start")
for term in [
    "HANDLE PortHandle = InterlockedExchangePointer(&m_hServerPort, NULL);",
    "for (i = 0; i < NUMBER_OF_THREADS; ++i) {",
    "NtRequestPort(PortHandle, msg);",
    "if (m_Threads && m_ThreadCount) {",
    "WaitForMultipleObjects(\n                                m_ThreadCount, m_Threads, TRUE, 5000)",
    "for (i = 0; i < m_ThreadCount; ++i)\n                TerminateThread(m_Threads[i], 0);",
    "WaitForMultipleObjects(m_ThreadCount, m_Threads, TRUE, 5000);",
    "CloseHandle(m_Threads[i]);",
    "m_Threads[i] = NULL;",
    "m_ThreadCount = 0;",
    "NtClose(PortHandle);",
]:
    require(shutdown, term, "ShutdownPortAndThreads")
if shutdown.index("if (m_Threads && m_ThreadCount)") > shutdown.index("WaitForMultipleObjects("):
    raise SystemExit("SREV-159 failed: counted wait gate is after wait")
if shutdown.index("CloseHandle(m_Threads[i]);") > shutdown.index("m_ThreadCount = 0;"):
    raise SystemExit("SREV-159 failed: thread count reset moved before handle close")
reject(shutdown, "NUMBER_OF_THREADS, m_Threads, TRUE, 5000", "full-vector wait in shutdown helper")

start = section(source, "bool PipeServer::Start()", "//---------------------------------------------------------------------------\n// ThreadStub")
for term in [
    "if (! m_Threads) {\n        SetLastError(ERROR_NOT_ENOUGH_MEMORY);\n        return false;\n    }",
    "ConvertStringSecurityDescriptorToSecurityDescriptor(",
    "NtCreatePort(",
    "m_Threads[i] = CreateThread(",
    "if (! m_Threads[i]) {",
    "ULONG error = GetLastError();",
    "LogEvent(MSG_9234, 0x9253, error);",
    "ShutdownPortAndThreads();",
    "SetLastError(error);",
    "return false;",
    "++m_ThreadCount;",
]:
    require(start, term, "Start")
if not (start.index("if (! m_Threads)") < start.index("ConvertStringSecurityDescriptorToSecurityDescriptor(")):
    raise SystemExit("SREV-159 failed: m_Threads allocation gate is after security descriptor/port work")
if not (start.index("ShutdownPortAndThreads();") < start.index("SetLastError(error);")):
    raise SystemExit("SREV-159 failed: partial startup cleanup does not preserve CreateThread error")
if start.index("++m_ThreadCount;") < start.index("if (! m_Threads[i])"):
    raise SystemExit("SREV-159 failed: thread count increments before CreateThread success gate")

for term in [
    "### SREV-159: PipeServer Thread Vector Lifetime",
    "PIPESERVER_THREAD_VECTOR_LIFETIME",
    "srev-159-pipeserver-thread-vector-lifetime.schema.json",
    "Sandboxie/core/svc/PipeServer.h",
    "Sandboxie/core/svc/PipeServer.cpp",
    "m_ThreadCount",
    "ShutdownPortAndThreads",
    "HeapAlloc",
    "CreateThread",
    "WaitForMultipleObjects",
    "CloseHandle",
    "HeapFree",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-159 schema/source gate passed")
