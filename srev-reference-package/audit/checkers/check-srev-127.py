#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-127 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-127 failed: {label} still contains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-127-namedpipe-lpc-name-wire-string.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-127 failed: schema is not draft-07")
if schema.get("id") != "NAMEDPIPE_LPC_NAME_WIRE_STRING":
    raise SystemExit("SREV-127 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "NAMED_PIPE_LPC_CONNECT_REQ name is a fixed-size wire field not a trusted C wide string until server termination",
    "LpcConnectHandler validates the full fixed request header before writing the local terminator into req->name",
    "LpcConnectHandler writes NUL to the last element of req->name before _wcsicmp wcscpy or wcscat consumes it",
    "existing allow-list remains limited to ntsvcs and plugplay",
    "RPC Control object path composition old LPC versus ALPC branch info validation and proxy-handle ownership are unchanged",
    "OpenHandler remains the nearby precedent for terminating fixed wire string fields before string operations",
]:
    require(contracts, term, "schema")

source = (ROOT / "Sandboxie/core/svc/namedpipeserver.cpp").read_text()
wire = (ROOT / "Sandboxie/core/svc/namedpipewire.h").read_text()
spec = (ROOT / "docs/plan/srev-127-namedpipe-lpc-name-wire-string.md").read_text()
ledger = read_combined_ledger(ROOT)

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "struct tagNAMED_PIPE_OPEN_REQ",
    "WCHAR name[64];",
    "WCHAR server[48];",
    "struct tagNAMED_PIPE_LPC_CONNECT_REQ",
    "WCHAR name[64];",
    "UCHAR info_data[1];",
]:
    require(wire, term, "wire schema")

open_handler = source[
    source.index("MSG_HEADER *NamedPipeServer::OpenHandler"):
    source.index("// CloseHandler")
]
lpc_connect = source[
    source.index("MSG_HEADER *NamedPipeServer::LpcConnectHandler"):
    source.index("// LpcRequestHandler")
]

for term in [
    "if (req->h.length < sizeof(NAMED_PIPE_OPEN_REQ))",
    "req->name[ARRAYSIZE(req->name) - 1] = L'\\0';",
    "req->server[ARRAYSIZE(req->server) - 1] = L'\\0';",
    "_wcsicmp(req->name, L\"lsarpc\")",
    "wcscat(pipename, req->name);",
]:
    require(open_handler, term, "OpenHandler fixed string precedent")

for term in [
    "if (req->h.length < sizeof(NAMED_PIPE_LPC_CONNECT_REQ))\n        goto finish;\n    req->name[ARRAYSIZE(req->name) - 1] = L'\\0';",
    "_wcsicmp(req->name, L\"ntsvcs\")",
    "_wcsicmp(req->name, L\"plugplay\")",
    "wcscpy(port_name, L\"\\\\RPC Control\\\\\");",
    "wcscat(port_name, req->name);",
    "if (req->info_len > PIPE_MAX_DATA_LEN)\n        goto finish;",
    "status = NtConnectPort(",
    "status = ((P_NtAlpcConnectPort)m_pNtAlpcConnectPort)(",
    "rpl->handle = m_ProxyHandle->Create(idProcess, &ProxyPipe);",
]:
    require(lpc_connect, term, "LpcConnectHandler")

if lpc_connect.index("req->name[ARRAYSIZE(req->name) - 1] = L'\\0';") > lpc_connect.index("_wcsicmp(req->name, L\"ntsvcs\")"):
    raise SystemExit("SREV-127 failed: req->name terminator is after _wcsicmp")

reject(lpc_connect, """if (req->h.length < sizeof(NAMED_PIPE_LPC_CONNECT_REQ))
        goto finish;

    WCHAR port_name[96];""", "unterminated LPC name old shape")

for term in [
    "### SREV-127: Named Pipe LPC Name Wire String",
    "NAMEDPIPE_LPC_NAME_WIRE_STRING",
    "srev-127-namedpipe-lpc-name-wire-string.schema.json",
    "Sandboxie/core/svc/namedpipeserver.cpp",
    "LpcConnectHandler",
    "NAMED_PIPE_LPC_CONNECT_REQ",
    "req->name",
    "_wcsicmp",
    "wcscat",
    "NtConnectPort",
    "NtAlpcConnectPort",
]:
    require(ledger, term, "ledger")

print("SREV-127 schema/source gate passed")
