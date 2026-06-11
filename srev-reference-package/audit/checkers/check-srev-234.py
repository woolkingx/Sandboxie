#!/usr/bin/env python3
import json
from pathlib import Path

from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-234 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-234 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-234-trace-header-topology.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-234 failed: schema is not draft-07")
if schema.get("id") != "TRACE_HEADER_TOPOLOGY_CONTRACT":
    raise SystemExit("SREV-234 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/dll/trace.h":
    raise SystemExit("SREV-234 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "DLL trace helper declaration header",
    "trace lifecycle helpers address lookup helpers",
    "does not own hook installation",
    "trace.c dllmain.c dllhook.c rpcrt.c file_misc.c sbieapi.c or callsvc.c",
    "caller topology and concrete runtime owner",
]:
    require(contracts, term, "schema contract")

spec = (ROOT / "docs/plan/srev-234-trace-header-topology.md").read_text()
header = (ROOT / "Sandboxie/core/dll/trace.h").read_text()
trace = (ROOT / "Sandboxie/core/dll/trace.c").read_text()
dllmain = (ROOT / "Sandboxie/core/dll/dllmain.c").read_text()
dllhook = (ROOT / "Sandboxie/core/dll/dllhook.c").read_text()
rpcrt = (ROOT / "Sandboxie/core/dll/rpcrt.c").read_text()
file_misc = (ROOT / "Sandboxie/core/dll/file_misc.c").read_text()
sbieapi = (ROOT / "Sandboxie/core/dll/sbieapi.c").read_text()
callsvc = (ROOT / "Sandboxie/core/dll/callsvc.c").read_text()
ledger = read_combined_ledger(ROOT)
fragment = (ROOT / "docs/plan/ledger/srev-234.md").read_text()

for term in [
    "int Trace_Init(void);",
    "void Trace_Entry(void);",
    "WCHAR* Trace_FindModuleByAddress(void* address);",
    "BOOLEAN Trace_FindExportByAddress(void* address, WCHAR** pModule, char** pExport, void** pAddress);",
    "void BufferToHexW(const void* lpBuffer, size_t nSize, wchar_t* outBuf, size_t outBufSize);",
    "extern BOOLEAN Dll_HookTrace;",
]:
    require(header, term, "header declaration")

for forbidden in [
    "SBIEDLL_HOOK",
    "NtSetInformationProcess",
    "SbieApi_MonitorPut",
    "Trace_SbieDrvFunc2Str",
    "Trace_SbieSvcFunc2Str",
    "Trace_SbieGuiFunc2Str",
    "ApiInstrumentation",
    "IMAGE_EXPORT_DIRECTORY",
]:
    reject(header, forbidden, "runtime owner code in header")

for term in [
    '#include "trace.h"',
    "_FX int Trace_Init(void)",
    "_FX void Trace_Entry(void)",
    "WCHAR* Trace_FindModuleByAddress(void* address)",
    "BOOLEAN Trace_FindExportByAddress(void* address, WCHAR** pModule, char** pExport, void** pAddress)",
    "NTSTATUS InstallInstrumentationCallback()",
    "VOID InstrumentationTrace(ULONG_PTR ReturnAddress, NTSTATUS ReturnStatus)",
    "void BufferToHexW(const void* lpBuffer, size_t nSize, wchar_t* outBuf, size_t outBufSize)",
    "const wchar_t* Trace_SbieDrvFunc2Str(ULONG func)",
    "const wchar_t* Trace_SbieSvcFunc2Str(ULONG func)",
    "const wchar_t* Trace_SbieGuiFunc2Str(ULONG func)",
]:
    require(trace, term, "trace.c owner topology")

for term in [
    '#include "trace.h"',
    "Trace_Init();",
    "Trace_Entry();",
]:
    require(dllmain, term, "dllmain caller topology")

for term in [
    '#include "trace.h"',
    "Trace_FindModuleByAddress((void*)module)",
    "TRACE_ENTRY* pTrace",
    "List_Insert_After(&mod_hook->trace, NULL, pTrace);",
]:
    require(dllhook, term, "dllhook caller topology")

for term in [
    '#include "trace.h"',
    "Trace_FindModuleByAddress((void*)pRetAddr)",
    "Trace_FindModuleByAddress(ReturnAddress)",
]:
    require(rpcrt, term, "rpcrt caller topology")

require(file_misc, "Trace_FindExportByAddress(lpBaseAddress, &pModule, &pExport, &pAddress)", "file_misc caller topology")

for term in [
    "extern const wchar_t* Trace_SbieDrvFunc2Str(ULONG func);",
    "Trace_SbieDrvFunc2Str((ULONG)parms[0])",
]:
    require(sbieapi, term, "sbieapi lookup topology")

for term in [
    "extern const wchar_t* Trace_SbieSvcFunc2Str(ULONG func);",
    "extern const wchar_t* Trace_SbieGuiFunc2Str(ULONG func);",
    "Trace_SbieSvcFunc2Str(req->msgid)",
]:
    require(callsvc, term, "callsvc lookup topology")

for term in [
    "SREV-093: Trace Instrumentation Private API Boundary",
    "owner: Sandboxie/core/dll/trace.c",
    "SREV-095: ARM64 API Instrumentation ABI",
    "owner: \"Sandboxie/core/dll/util_arm.asm:436\"",
    "SREV-177: ARM64EC API Instrumentation Argument Preservation",
    "owner: Sandboxie/core/dll/util_EC.asm",
    "SREV-028: Monitor Get Uses Wrong Entry Payload Size",
    "SREV-220: Session MonitorGet2 Buffer Floor",
]:
    require(ledger, term, "existing trace/monitor owner coverage")

for term in [
    "No source patch",
    "declaration/topology header",
    "No new Windows/API runtime behavior is defined by this header",
    "concrete-owner SREV Windows gates",
]:
    require(spec, term, "spec classification")

for term in [
    "kind: srev-ledger-entry",
    "id: SREV-234",
    "owner: Sandboxie/core/dll/trace.h",
    "docs-only-source-topology-reviewed",
    "srev-234-trace-header-topology.schema.json",
    "check-srev-234.py",
]:
    require(fragment, term, "ledger fragment")
    require(ledger, term, "combined ledger")

print("SREV-234 source gate passed")
