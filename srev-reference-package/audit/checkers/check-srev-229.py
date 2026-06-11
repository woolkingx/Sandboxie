#!/usr/bin/env python3
import json
from pathlib import Path

from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-229 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-229 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-229-epmapper-server-header-topology.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-229 failed: schema is not draft-07")
if schema.get("id") != "EPMAPPER_SERVER_HEADER_TOPOLOGY_CONTRACT":
    raise SystemExit("SREV-229 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/svc/EpMapperServer.h":
    raise SystemExit("SREV-229 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "declaration-only service header",
    "service class, constructor, static PipeServer handler",
    "does not own RPC endpoint parsing",
    "EpMapperServer.cpp, EpMapperWire.h, rpcrt.c, or ipc_port.c",
    "PipeServer registration and dispatch topology",
]:
    require(contracts, term, "schema contract")

spec = (ROOT / "docs/plan/srev-229-epmapper-server-header-topology.md").read_text()
header = (ROOT / "Sandboxie/core/svc/EpMapperServer.h").read_text()
source = (ROOT / "Sandboxie/core/svc/EpMapperServer.cpp").read_text()
main = (ROOT / "Sandboxie/core/svc/main.cpp").read_text()
wire = (ROOT / "Sandboxie/core/svc/EpMapperWire.h").read_text()
ledger = read_combined_ledger(ROOT)
fragment = (ROOT / "docs/plan/ledger/srev-229.md").read_text()

for term in [
    '#include "PipeServer.h"',
    "class EpMapperServer",
    "EpMapperServer(PipeServer *pipeServer);",
    "static MSG_HEADER *Handler(void *_this, MSG_HEADER *msg);",
    "MSG_HEADER *EpmapperGetPortNameHandler(MSG_HEADER *msg);",
]:
    require(header, term, "header declaration")

for forbidden in [
    "RpcMgmtEpEltInqBegin",
    "RpcMgmtEpEltInqNextW",
    "RpcBindingToStringBindingW",
    "SbieApi_Call(",
    "EPMAPPER_GET_PORT_NAME_REQ",
    "API_OPEN_DYNAMIC_PORT",
]:
    reject(header, forbidden, "runtime owner code in header")

for term in [
    "EpMapperServer::EpMapperServer(PipeServer *pipeServer)",
    "pipeServer->Register(MSGID_EPMAPPER, this, Handler);",
    "MSG_HEADER *EpMapperServer::Handler(void *_this, MSG_HEADER *msg)",
    "if (msg->msgid == MSGID_EPMAPPER_GET_PORT_NAME)",
    "return pThis->EpmapperGetPortNameHandler(msg);",
    "MSG_HEADER *EpMapperServer::EpmapperGetPortNameHandler(MSG_HEADER *msg)",
]:
    require(source, term, "source dispatch topology")

require(main, "new EpMapperServer(pipeServer);", "main startup topology")
for term in [
    "struct tagEPMAPPER_GET_PORT_NAME_REQ",
    "WCHAR wszPortId[DYNAMIC_PORT_ID_CHARS];",
    "struct tagEPMAPPER_GET_PORT_NAME_RPL",
    "WCHAR wszPortName[DYNAMIC_PORT_NAME_CHARS];",
]:
    require(wire, term, "wire owner topology")

for term in [
    "SREV-108 already owns the dynamic-port scope",
    "SREV-218 already owns the fixed wire string",
    "No source patch",
    "local service-topology classification",
]:
    require(spec, term, "spec classification")

for term in [
    "### SREV-108: EpMapper Dynamic Port Scope And Binding Lifetime",
    "owner: Sandboxie/core/svc/EpMapperServer.cpp",
    "### SREV-218: EpMapper Fixed Wire String Contract",
    "owner: Sandboxie/core/svc/EpMapperWire.h",
    "Sandboxie/core/svc/EpMapperServer.cpp",
    "Sandboxie/core/dll/rpcrt.c",
    "Sandboxie/core/drv/ipc_port.c",
]:
    require(ledger, term, "existing owner coverage")

for term in [
    "kind: srev-ledger-entry",
    "id: SREV-229",
    "owner: Sandboxie/core/svc/EpMapperServer.h",
    "docs-only-source-topology-reviewed",
    "srev-229-epmapper-server-header-topology.schema.json",
    "check-srev-229.py",
]:
    require(fragment, term, "ledger fragment")
    require(ledger, term, "combined ledger")

print("SREV-229 source gate passed")
