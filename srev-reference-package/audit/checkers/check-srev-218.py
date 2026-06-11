#!/usr/bin/env python3
import json
from pathlib import Path

from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-218 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-218 failed: stale {label} remains {needle!r}")


def between(text: str, start: str, end: str) -> str:
    a = text.index(start)
    b = text.index(end, a + len(start))
    return text[a:b]


schema = json.loads(
    (ROOT / "docs/plan/srev-218-epmapper-fixed-wire-string-contract.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-218 failed: schema is not draft-07")
if schema.get("id") != "EPMAPPER_FIXED_WIRE_STRING_CONTRACT":
    raise SystemExit("SREV-218 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/svc/EpMapperWire.h":
    raise SystemExit("SREV-218 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "fixed service wire fields",
    "non-empty and null-terminated inside the field",
    "bounded-copies port ids and cached port names",
    "bounded local portId before policy lookup",
    "validated ncalrpc:[endpoint] string binding",
    "does not use magic offsets",
    "driver API_OPEN_DYNAMIC_PORT path keeps its fixed user-string copy gate",
]:
    require(contracts, term, "schema contract")

spec = (ROOT / "docs/plan/srev-218-epmapper-fixed-wire-string-contract.md").read_text()
wire = (ROOT / "Sandboxie/core/svc/EpMapperWire.h").read_text()
dll = (ROOT / "Sandboxie/core/dll/rpcrt.c").read_text()
svc = (ROOT / "Sandboxie/core/svc/EpMapperServer.cpp").read_text()
driver = (ROOT / "Sandboxie/core/drv/ipc_port.c").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-218.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "WCHAR wszPortId[DYNAMIC_PORT_ID_CHARS];",
    "WCHAR wszPortName[DYNAMIC_PORT_NAME_CHARS];",
    "h.status is RPC_STATUS",
]:
    require(wire, term, "wire header")

for term in [
    "static BOOLEAN RpcRt_CopyFixedWString(",
    "wmemzero(dst, dst_chars);",
    "for (i = 0; i < dst_chars; ++i)",
    "if (i == dst_chars - 1)",
    "return i != 0;",
    "RpcRt_CopyFixedWString(portId, DYNAMIC_PORT_ID_CHARS, wszPortId)",
    "RpcRt_CopyFixedWString(portName, DYNAMIC_PORT_NAME_CHARS, wszPortName)",
    "RpcRt_CopyFixedWString(req.wszPortId, DYNAMIC_PORT_ID_CHARS, wszPortId)",
    "wmemcpy(port->wstrPortId, portId, DYNAMIC_PORT_ID_CHARS)",
    "wmemcpy(port->wstrPortName, portName, DYNAMIC_PORT_NAME_CHARS)",
]:
    require(dll, term, "DLL fixed-string gate")

reject(dll, "wcscpy(req.wszPortId, wszPortId)", "unbounded request copy")
reject(dll, "wmemcpy(port->wstrPortId, wszPortId, DYNAMIC_PORT_ID_CHARS)", "unbounded cache id copy")
reject(dll, "wmemcpy(port->wstrPortName, wszPortName, DYNAMIC_PORT_NAME_CHARS)", "unbounded cache name copy")

handler = between(
    svc,
    "MSG_HEADER *EpMapperServer::EpmapperGetPortNameHandler(MSG_HEADER *msg)",
    "\n    return (MSG_HEADER *)rpl;",
)
for term in [
    "static bool EpMapper_CopyFixedWString(",
    "static bool EpMapper_CopyNcalrpcEndpoint(",
    "EpMapper_CopyFixedWString(portId, DYNAMIC_PORT_ID_CHARS, req->wszPortId)",
    "_wcsicmp(portId, SPOOLER_PORT_ID)",
    "SbieDll_GetStringForStringList(portId, boxname, L\"RpcPortBindingIfId\"",
    "SbieDll_GetStringForStringList(portId, boxname, L\"RpcPortBindingSvc\"",
    "std::wstring(L\"Open\") + portId + L\"Endpoint\"",
    "SbieDll_GetStringsForStringList(portId, boxname, L\"RpcPortFilter\"",
    "(ULONG_PTR)portId,",
]:
    require(svc, term, "service fixed-string gate")

for term in [
    "_wcsnicmp(str, L\"ncalrpc:[\", 9) != 0",
    "endpoint = str + 9;",
    "end = wcschr(endpoint, L']');",
    "if (!end || end == endpoint)",
    "for (i = 0; endpoint + i < end && i < dst_chars - 1; ++i)",
    "if (endpoint + i != end)",
    "EpMapper_CopyNcalrpcEndpoint(wstrPortName, DYNAMIC_PORT_NAME_CHARS, pwszPortName)",
    "rpl->wszPortName[DYNAMIC_PORT_NAME_CHARS - 1] = L'\\0';",
]:
    require(svc, term, "ncalrpc endpoint parser")

reject(handler, "_wcsicmp(req->wszPortId", "direct request port id compare")
reject(handler, "SbieDll_GetStringForStringList(req->wszPortId", "direct request port id lookup")
reject(handler, "SbieDll_GetStringsForStringList(req->wszPortId", "direct request port id filter lookup")
reject(handler, "std::wstring(L\"Open\") + req->wszPortId", "direct request port id setting composition")
reject(handler, "(ULONG_PTR)req->wszPortId", "direct request port id driver call")
reject(svc, "(wchar_t*)pwszPortName + 9", "magic endpoint offset")
reject(svc, "wstrPortName[23] = 0", "hard-coded endpoint length")

for term in [
    "static NTSTATUS Ipc_CopyFixedUserWString(",
    "Ipc_CopyFixedUserWString(",
    "portName, pArgs->port_name.val, DYNAMIC_PORT_NAME_CHARS",
    "portId, pArgs->port_id.val, DYNAMIC_PORT_ID_CHARS",
    "wmemcpy(port->wstrPortId, PortId, DYNAMIC_PORT_ID_CHARS)",
    "wmemcpy(port->wstrPortName, PortName, DYNAMIC_PORT_NAME_CHARS)",
]:
    require(driver, term, "driver fixed-string gate")

for term in [
    "kind: srev-ledger-entry",
    "id: SREV-218",
    "owner: Sandboxie/core/svc/EpMapperWire.h",
    "spec: docs/plan/srev-218-epmapper-fixed-wire-string-contract.md",
    "schema: docs/plan/srev-218-epmapper-fixed-wire-string-contract.schema.json",
    "checker: docs/plan/check-srev-218.py",
    "patched-source-level-after-official-rpc-string-binding-and-msvc-fixed-string-review",
]:
    require(ledger_fragment, term, "ledger fragment")
    require(ledger, term, "combined ledger")

print("SREV-218 source gate passed")
