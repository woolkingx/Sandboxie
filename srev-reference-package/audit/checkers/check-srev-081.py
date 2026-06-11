#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-081 failed: {label} missing {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-081-pipeserver-appcontainer-port-dacl.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-081 failed: schema is not draft-07")
if schema.get("id") != "PIPESERVER_APPCONTAINER_PORT_DACL":
    raise SystemExit("SREV-081 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "service side owns the named port security descriptor",
    "must not bypass AppContainer token semantics",
    "legacy any-process connect shape through WD",
    "explicit AC ACE",
    "fall back to an explicit WD DACL",
    "must not be published with a NULL DACL",
]:
    require(contracts, term, "schema")

src = (ROOT / "Sandboxie/core/svc/PipeServer.cpp").read_text()
callsvc = (ROOT / "Sandboxie/core/dll/callsvc.c").read_text()
spec = (ROOT / "docs/plan/srev-081-pipeserver-appcontainer-port-dacl.md").read_text()
ledger = read_combined_ledger(ROOT)

for term in [
    "#include <sddl.h>",
    "ConvertStringSecurityDescriptorToSecurityDescriptor(",
    "L\"O:SYG:SYD:(A;;GA;;;WD)(A;;GA;;;AC)\"",
    "L\"O:SYG:SYD:(A;;GA;;;WD)\"",
    "SDDL_REVISION_1",
    "LocalFree(sd);",
    "InitializeObjectAttributes(\n        &objattrs, &PortName, OBJ_CASE_INSENSITIVE, NULL, sd)",
]:
    require(src, term, "PipeServer source")

start = src.index("bool PipeServer::Start()")
end = src.index("InterlockedExchangePointer(&m_hServerPort", start)
start_func = src[start:end]

for stale in [
    "SetSecurityDescriptorDacl(sd, TRUE, NULL, FALSE)",
    "ULONG sd_space[16]",
    "server port should have a NULL DACL",
]:
    if stale in start_func:
        raise SystemExit(f"SREV-081 failed: stale NULL-DACL shape remains: {stale}")

for term in [
    "AppContainer service-port access is owned by PipeServer's DACL;",
    "avoid noisy client logging here while SREV-081 remains runtime-gated.",
    "Dll_AppContainerToken",
]:
    require(callsvc, term, "callsvc evidence")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "### SREV-081: PipeServer AppContainer Port DACL",
    "PIPESERVER_APPCONTAINER_PORT_DACL",
    "srev-081-pipeserver-appcontainer-port-dacl.schema.json",
]:
    require(ledger, term, "ledger")

print("SREV-081 schema/source gate passed")
