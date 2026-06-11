#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-195 failed: {label} missing {needle!r}")


def between(text: str, start: str, end: str) -> str:
    a = text.index(start)
    b = text.index(end, a + len(start))
    return text[a:b]


schema = json.loads(
    (ROOT / "docs/plan/srev-195-com-blanket-wire-string-contract.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-195 failed: schema is not draft-07")
if schema.get("id") != "COM_BLANKET_WIRE_STRING_CONTRACT":
    raise SystemExit("SREV-195 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/svc/comserver.cpp":
    raise SystemExit("SREV-195 failed: wrong owner")
if schema.get("entry_surface") != "Sandboxie/core/svc/comserver.h":
    raise SystemExit("SREV-195 failed: wrong entry surface")

contracts = "\n".join(schema["contracts"])
for term in [
    "comserver.h declares the QueryBlanket and SetBlanket handler boundary",
    "COM_SET_BLANKET_REQ ServerPrincName is a fixed WCHAR array",
    "DefaultServerPrincName maps to COLE_DEFAULT_PRINCIPAL",
    "non-default ServerPrincName must terminate inside the fixed wire field",
    "SetBlanketHandler validates the terminator before shared-map copy",
    "SetBlanketSlave validates the terminator before CoSetProxyBlanket",
    "CoQueryProxyBlanket returned principal is released with CoTaskMemFree",
    "QueryBlanketSlave sets BufferLength to sizeof COM_QUERY_BLANKET_RPL",
    "QueryBlanketHandler validates BufferLength before copying reply fields",
]:
    require(contracts, term, "schema contracts")

com_h = (ROOT / "Sandboxie/core/svc/comserver.h").read_text()
wire = (ROOT / "Sandboxie/core/svc/comwire.h").read_text()
svc = (ROOT / "Sandboxie/core/svc/comserver.cpp").read_text()
dll = (ROOT / "Sandboxie/core/dll/com.c").read_text()
spec = (ROOT / "docs/plan/srev-195-com-blanket-wire-string-contract.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-195.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "MSG_HEADER *QueryBlanketHandler(",
    "MSG_HEADER *SetBlanketHandler(",
    "static void QueryBlanketSlave(",
    "static void SetBlanketSlave(",
]:
    require(com_h, term, "comserver.h declaration surface")

for term in [
    "struct tagCOM_QUERY_BLANKET_RPL",
    "WCHAR ServerPrincName[128];",
    "struct tagCOM_SET_BLANKET_REQ",
    "BOOLEAN DefaultServerPrincName;",
]:
    require(wire, term, "comwire blanket records")

for term in [
    "req.ServerPrincName[0] = L'\\0';",
    "req.DefaultServerPrincName = FALSE;",
    "req.DefaultServerPrincName = TRUE;",
    "req.ServerPrincName[copy_len / sizeof(WCHAR)] = L'\\0';",
]:
    require(dll, term, "DLL producer shape")

helper = between(
    svc,
    "static bool ComServer_HasWcharTerminator(",
    "//---------------------------------------------------------------------------\n// Constructor",
)
for term in [
    "if (! text)",
    "for (i = 0; i < chars; ++i)",
    "if (text[i] == L'\\0')",
    "return true;",
]:
    require(helper, term, "terminator helper")

query_handler = between(
    svc,
    "MSG_HEADER *ComServer::QueryBlanketHandler(",
    "//---------------------------------------------------------------------------\n// SetBlanketHandler",
)
for term in [
    "if (pMap->BufferLength != sizeof(COM_QUERY_BLANKET_RPL))",
    "return SHORT_REPLY(RPC_S_INVALID_TAG);",
    "COM_QUERY_BLANKET_RPL *buf = (COM_QUERY_BLANKET_RPL *)pMap->Buffer;",
    "memcpy(rpl->ServerPrincName, buf->ServerPrincName,",
]:
    require(query_handler, term, "QueryBlanketHandler reply gate")
if not query_handler.index("if (pMap->BufferLength != sizeof(COM_QUERY_BLANKET_RPL))") < query_handler.index("COM_QUERY_BLANKET_RPL *rpl"):
    raise SystemExit("SREV-195 failed: QueryBlanketHandler validates reply too late")

set_handler = between(
    svc,
    "MSG_HEADER *ComServer::SetBlanketHandler(",
    "//---------------------------------------------------------------------------\n// CopyProxyHandler",
)
for term in [
    "if ((! req->DefaultServerPrincName) &&",
    "ComServer_HasWcharTerminator(",
    "req->ServerPrincName,",
    "sizeof(req->ServerPrincName) / sizeof(WCHAR)",
    "return SHORT_REPLY(E_INVALIDARG);",
    "memcpy(pMap->Buffer, req, sizeof(COM_SET_BLANKET_REQ));",
]:
    require(set_handler, term, "SetBlanketHandler terminator gate")
if not set_handler.index("ComServer_HasWcharTerminator(") < set_handler.index("memcpy(pMap->Buffer, req, sizeof(COM_SET_BLANKET_REQ));"):
    raise SystemExit("SREV-195 failed: SetBlanketHandler copies before terminator gate")

query_slave = between(
    svc,
    "void ComServer::QueryBlanketSlave(",
    "//---------------------------------------------------------------------------\n// SetBlanketSlave",
)
for term in [
    "CoQueryProxyBlanket(",
    "CoTaskMemFree(ServerPrincName);",
    "pMap->BufferLength = sizeof(COM_QUERY_BLANKET_RPL);",
]:
    require(query_slave, term, "QueryBlanketSlave reply contract")
if not query_slave.index("CoQueryProxyBlanket(") < query_slave.index("pMap->BufferLength = sizeof(COM_QUERY_BLANKET_RPL);"):
    raise SystemExit("SREV-195 failed: QueryBlanketSlave publishes size before query")

set_slave = between(
    svc,
    "void ComServer::SetBlanketSlave(",
    "//---------------------------------------------------------------------------\n// CopyProxySlave",
)
for term in [
    "if ((! buf->DefaultServerPrincName) &&",
    "ComServer_HasWcharTerminator(",
    "buf->ServerPrincName,",
    "sizeof(buf->ServerPrincName) / sizeof(WCHAR)",
    "*exc = RPC_S_INVALID_TAG;",
    "*hr = E_ABORT;",
    "pServerPrincName = COLE_DEFAULT_PRINCIPAL;",
    "CoSetProxyBlanket(",
]:
    require(set_slave, term, "SetBlanketSlave terminator gate")
if not set_slave.index("ComServer_HasWcharTerminator(") < set_slave.index("CoSetProxyBlanket("):
    raise SystemExit("SREV-195 failed: SetBlanketSlave calls COM before terminator gate")

for term in [
    "kind: srev-ledger-entry",
    "id: SREV-195",
    "owner: Sandboxie/core/svc/comserver.cpp",
    "spec: docs/plan/srev-195-com-blanket-wire-string-contract.md",
    "schema: docs/plan/srev-195-com-blanket-wire-string-contract.schema.json",
    "checker: docs/plan/check-srev-195.py",
]:
    require(ledger_fragment, term, "ledger fragment header")

for term in [
    "### SREV-195: COM Blanket Wire String Contract",
    "COM_BLANKET_WIRE_STRING_CONTRACT",
    "Sandboxie/core/svc/comserver.h",
    "Sandboxie/core/svc/comserver.cpp",
    "Sandboxie/core/svc/comwire.h",
    "CoSetProxyBlanket",
    "CoQueryProxyBlanket",
    "ComServer_HasWcharTerminator",
]:
    require(ledger, term, "combined ledger")

print("SREV-195 schema/source gate passed")
