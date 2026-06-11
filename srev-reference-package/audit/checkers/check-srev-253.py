#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-253 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-253 failed: {label} still contains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-253-callsvc-appcontainer-dacl-boundary.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-253 failed: schema is not draft-07")
if schema.get("id") != "CALLSVC_APPCONTAINER_DACL_BOUNDARY":
    raise SystemExit("SREV-253 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "PipeServer::Start not by client-side token bypass",
    "service port DACL carrying the AppContainer side",
    "suppress noisy connection logs",
    "must not impersonate revert",
    "SREV-081 remains the behavior owner",
    "does not change NtConnectPort",
]:
    require(contracts, term, "schema")

callsvc = (ROOT / "Sandboxie/core/dll/callsvc.c").read_text()
pipeserver = (ROOT / "Sandboxie/core/svc/PipeServer.cpp").read_text()
srev_081 = (ROOT / "docs/plan/srev-081-pipeserver-appcontainer-port-dacl.md").read_text()
srev_081_check = (ROOT / "docs/plan/check-srev-081.py").read_text()
spec = (ROOT / "docs/plan/srev-253-callsvc-appcontainer-dacl-boundary.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-253.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")
    require(srev_081, term, "SREV-081 official reference")

for term in [
    "AppContainer service-port access is owned by PipeServer's DACL;",
    "avoid noisy client logging here while SREV-081 remains runtime-gated.",
    "if (!Dll_AppContainerToken && !Silent)",
    "SbieApi_Log(2203, L\"connect %08X (msg_id 0x%04X)\", status, req->msgid);",
    "status = SbieDll_ConnectPort();",
]:
    require(callsvc, term, "callsvc.c")

reject(callsvc, "todo: fix me make service available for appcontainer processes", "callsvc.c")

for term in [
    "L\"O:SYG:SYD:(A;;GA;;;WD)(A;;GA;;;AC)\"",
    "L\"O:SYG:SYD:(A;;GA;;;WD)\"",
    "ConvertStringSecurityDescriptorToSecurityDescriptor(",
    "LocalFree(sd);",
]:
    require(pipeserver, term, "PipeServer.cpp")

for term in [
    "AppContainer service-port access is owned by PipeServer's DACL;",
    "avoid noisy client logging here while SREV-081 remains runtime-gated.",
]:
    require(srev_081_check, term, "SREV-081 checker adjacency")

for term in [
    "client-side",
    "comment routing to the service-owned DACL boundary",
    "SbieDll_ConnectPort / NtConnectPort",
]:
    require(srev_081, term, "SREV-081 adjacency")

for term in [
    "### SREV-253: Callsvc AppContainer DACL Boundary",
    "CALLSVC_APPCONTAINER_DACL_BOUNDARY",
    "srev-253-callsvc-appcontainer-dacl-boundary.schema.json",
    "Sandboxie/core/dll/callsvc.c",
    "Sandboxie/core/svc/PipeServer.cpp",
    "SREV-081",
    "AppContainer",
    "NtConnectPort",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-253 source gate passed")
