#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-093 failed: {label} missing {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-093-trace-instrumentation-private-api-boundary.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-093 failed: schema is not draft-07")
if schema.get("id") != "TRACE_INSTRUMENTATION_PRIVATE_API_BOUNDARY":
    raise SystemExit("SREV-093 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "CallTraceEx may request a process instrumentation callback only through the trace owner",
    "ProcessInstrumentationCallback is a private NtSetInformationProcess class",
    "public SetProcessInformation documentation does not define the instrumentation callback class",
    "pre-10041 privilege behavior must stay fail-closed",
    "AdjustTokenPrivileges cannot add SeDebugPrivilege",
    "driver-mediated privilege or temporary privilege enablement is not a source-only fix",
    "ARM64EC is not covered by the native ARM64 callback restore path",
]:
    require(contracts, term, "schema")

trace = (ROOT / "Sandboxie/core/dll/trace.c").read_text()
ntddk = (ROOT / "Sandboxie/common/win32_ntddk.h").read_text()
spec = (ROOT / "docs/plan/srev-093-trace-instrumentation-private-api-boundary.md").read_text()
ledger = read_combined_ledger(ROOT)

for term in [
    "SbieApi_QueryConf(NULL, L\"CallTraceEx\"",
    "PROCESS_INSTRUMENTATION_CALLBACK_INFORMATION",
    "CallbackInfo.Callback = InstrumentationCallbackAsm;",
    "NtSetInformationProcess(ProcessHandle, ProcessInstrumentationCallback, &CallbackInfo, sizeof(CallbackInfo))",
    "ProcessInstrumentationCallback is a private NtSetInformationProcess class.",
    "keep this fail-closed until a runtime matrix proves",
    "driver-mediated or temporary privilege-enable path",
    "if (Dll_OsBuild < 10041)\n        return STATUS_PRIVILEGE_NOT_HELD;",
    "callback restore path is not a proven ARM64EC instrumentation ABI.",
    "return STATUS_NOT_SUPPORTED;",
]:
    require(trace, term, "trace.c private instrumentation boundary")

for stale in [
    "todo: use sbie drv or set privilege in compartment type boxes",
    "// TODO",
]:
    if stale in trace:
        raise SystemExit(f"SREV-093 failed: stale trace TODO remains {stale!r}")

for term in [
    "typedef enum _PROCESSINFOCLASS",
    "ProcessInstrumentationCallback,\t\t\t\t\t\t// 40",
]:
    require(ntddk, term, "local PROCESSINFOCLASS declaration")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "public API shape does not define the instrumentation callback class",
    "AdjustTokenPrivileges cannot add privileges",
    "Arm64EC is deliberately x64-compatible and thunked",
    "No behavior was changed.",
]:
    require(spec, term, "spec source/API classification")

for term in [
    "### SREV-093: Trace Instrumentation Private API Boundary",
    "TRACE_INSTRUMENTATION_PRIVATE_API_BOUNDARY",
    "srev-093-trace-instrumentation-private-api-boundary.schema.json",
]:
    require(ledger, term, "ledger")

print("SREV-093 schema/source gate passed")
