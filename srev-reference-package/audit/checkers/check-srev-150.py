#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-150 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-150 failed: {label} still contains {needle!r}")


def between(text: str, start: str, end: str) -> str:
    a = text.index(start)
    b = text.index(end, a + len(start))
    return text[a:b]


schema = json.loads(
    (ROOT / "docs/plan/srev-150-com-invoke-wire-buffer-bound.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-150 failed: schema is not draft-07")
if schema.get("id") != "COM_INVOKE_WIRE_BUFFER_BOUND":
    raise SystemExit("SREV-150 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "RPCOLEMESSAGE.cbBuffer is a byte count for the marshaled method buffer",
    "The local COM invoke wire payload must fit in the SbieSvc shared COM map before the DLL allocates and copies it",
    "DLL sender and service receiver must use the same named maximum for invoke method payload bytes",
    "Flexible-tail request length must be computed from FIELD_OFFSET(COM_INVOKE_METHOD_REQ, Buffer) + BufferLength",
    "The service receiver remains the authority that copies a schema-valid invoke request into the slave map; this SREV does not change COM policy",
]:
    require(contracts, term, "schema")

wire = (ROOT / "Sandboxie/core/svc/comwire.h").read_text()
dll = (ROOT / "Sandboxie/core/dll/com.c").read_text()
svc = (ROOT / "Sandboxie/core/svc/comserver.cpp").read_text()
spec = (ROOT / "docs/plan/srev-150-com-invoke-wire-buffer-bound.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-150.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "#define COM_SLAVE_MAP_SIZE        (PAGE_SIZE * 512)",
    "#define COM_SLAVE_MAP_HEADER_LEN  (sizeof(ULONG) * 6)",
    "#define COM_MAX_INVOKE_BUF_LEN    (COM_SLAVE_MAP_SIZE - COM_SLAVE_MAP_HEADER_LEN)",
    "struct tagCOM_INVOKE_METHOD_REQ",
    "ULONG BufferLength;",
    "WCHAR Buffer[1];",
]:
    require(wire, term, "comwire.h")

sendrecv = between(
    dll,
    "_FX HRESULT Com_IRpcChannelBuffer_SendReceive(",
    "//---------------------------------------------------------------------------\n// SbieDll_IRpcChannelBuffer_New",
)
for term in [
    "if (pMessage->BufferLength >= COM_MAX_INVOKE_BUF_LEN)",
    "return MEM_E_INVALID_SIZE;",
    "len = FIELD_OFFSET(COM_INVOKE_METHOD_REQ, Buffer) + pMessage->BufferLength;",
    "req = (COM_INVOKE_METHOD_REQ *)Com_Alloc(len);",
    "req->BufferLength = pMessage->BufferLength;",
    "memcpy(req->Buffer, pMessage->Buffer, pMessage->BufferLength);",
]:
    require(sendrecv, term, "Com_IRpcChannelBuffer_SendReceive")
reject(
    sendrecv,
    "len = sizeof(COM_INVOKE_METHOD_REQ) + pMessage->BufferLength;",
    "stale invoke request length",
)
if not (
    sendrecv.index("if (pMessage->BufferLength >= COM_MAX_INVOKE_BUF_LEN)")
    < sendrecv.index("len = FIELD_OFFSET(COM_INVOKE_METHOD_REQ, Buffer) + pMessage->BufferLength;")
    < sendrecv.index("req = (COM_INVOKE_METHOD_REQ *)Com_Alloc(len);")
    < sendrecv.index("memcpy(req->Buffer, pMessage->Buffer, pMessage->BufferLength);")
):
    raise SystemExit("SREV-150 failed: DLL sender bound/order is wrong")

for term in [
    "#define MAX_MAP_BUFFER_LENGTH \\",
    "COM_MAX_INVOKE_BUF_LEN",
]:
    require(svc, term, "comserver.cpp shared max")
invoke = between(
    svc,
    "MSG_HEADER *ComServer::InvokeMethodHandler(",
    "//---------------------------------------------------------------------------\n// UnmarshalInterfaceHandler",
)
for term in [
    "if (req->BufferLength >= MAX_MAP_BUFFER_LENGTH)",
    "ULONG offset = FIELD_OFFSET(COM_INVOKE_METHOD_REQ, Buffer);",
    "if (offset + req->BufferLength > req->h.length)",
    "memcpy(pMap->Buffer, req->Buffer, req->BufferLength);",
]:
    require(invoke, term, "InvokeMethodHandler")

for term in [
    "Sandboxie/core/svc/comwire.h",
    "Sandboxie/core/dll/com.c",
    "Sandboxie/core/svc/comserver.cpp",
    "### SREV-150: COM Invoke Wire Buffer Bound",
    "COM_INVOKE_WIRE_BUFFER_BOUND",
    "srev-150-com-invoke-wire-buffer-bound.schema.json",
    "RPCOLEMESSAGE",
    "IRpcChannelBuffer::SendReceive",
    "COM_MAX_INVOKE_BUF_LEN",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-150 schema/source gate passed")
