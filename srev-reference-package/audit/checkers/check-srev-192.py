#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-192 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-192 failed: {label} still contains {needle!r}")


def between(text: str, start: str, end: str) -> str:
    a = text.index(start)
    b = text.index(end, a + len(start))
    return text[a:b]


schema = json.loads(
    (ROOT / "docs/plan/srev-192-gui-copydata-wire-length-contract.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-192 failed: schema is not draft-07")
if schema.get("id") != "GUI_COPYDATA_WIRE_LENGTH_CONTRACT":
    raise SystemExit("SREV-192 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/svc/GuiWire.h":
    raise SystemExit("SREV-192 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "GUI_SEND_COPYDATA_REQ wire shape",
    "cbData is a byte count",
    "lpData is generic PVOID data",
    "cds_buf is a byte tail",
    "FIELD_OFFSET before reading cds_len",
    "enum request id GUI_SEND_COPYDATA is not a structure size owner",
    "FIELD_OFFSET plus cds_len fits inside req_len",
    "allocate FIELD_OFFSET plus byte payload length",
]:
    require(contracts, term, "schema contracts")

wire = (ROOT / "Sandboxie/core/svc/GuiWire.h").read_text()
svc = (ROOT / "Sandboxie/core/svc/GuiServer.cpp").read_text()
guimsg = (ROOT / "Sandboxie/core/dll/guimsg.c").read_text()
guidde = (ROOT / "Sandboxie/core/dll/guidde.c").read_text()
spec = (ROOT / "docs/plan/srev-192-gui-copydata-wire-length-contract.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-192.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "struct tagGUI_SEND_COPYDATA_REQ",
    "ULONG cds_len;",
    "UCHAR cds_buf[1];",
]:
    require(wire, term, "GuiWire copydata shape")
reject(wire, "WCHAR cds_buf[1];", "stale wide copydata tail")

send_copydata = between(
    svc,
    "ULONG GuiServer::SendCopyDataSlave(",
    "//---------------------------------------------------------------------------\n// ShellNotifyIconSlave",
)
for term in [
    "const ULONG fixed_len = FIELD_OFFSET(GUI_SEND_COPYDATA_REQ, cds_buf);",
    "if (args->req_len < fixed_len)",
    "if (req->cds_len > 1024*1024)",
    "ULONG max_offset = fixed_len + req->cds_len;",
    "if (max_offset < fixed_len || max_offset > args->req_len)",
    "cds.cbData = req->cds_len;",
    "cds.lpData = req->cds_buf;",
]:
    require(send_copydata, term, "SendCopyDataSlave")
reject(send_copydata, "sizeof(GUI_SEND_COPYDATA)", "enum-size request gate")
if not (
    send_copydata.index("const ULONG fixed_len = FIELD_OFFSET(GUI_SEND_COPYDATA_REQ, cds_buf);")
    < send_copydata.index("if (args->req_len < fixed_len)")
    < send_copydata.index("if (req->cds_len > 1024*1024)")
    < send_copydata.index("ULONG max_offset = fixed_len + req->cds_len;")
    < send_copydata.index("if (max_offset < fixed_len || max_offset > args->req_len)")
    < send_copydata.index("COPYDATASTRUCT cds;")
):
    raise SystemExit("SREV-192 failed: SendCopyDataSlave validation order is wrong")

for src, label in [(guimsg, "guimsg.c"), (guidde, "guidde.c")]:
    require(
        src,
        "FIELD_OFFSET(GUI_SEND_COPYDATA_REQ, cds_buf)",
        f"{label} fixed-header allocation",
    )
    reject(
        src,
        "sizeof(GUI_SEND_COPYDATA_REQ) +",
        f"{label} stale sizeof allocation",
    )

for term in [
    "kind: srev-ledger-entry",
    "id: SREV-192",
    "owner: Sandboxie/core/svc/GuiWire.h",
    "spec: docs/plan/srev-192-gui-copydata-wire-length-contract.md",
    "schema: docs/plan/srev-192-gui-copydata-wire-length-contract.schema.json",
    "checker: docs/plan/check-srev-192.py",
]:
    require(ledger_fragment, term, "ledger fragment header")

for term in [
    "### SREV-192: GUI COPYDATA Wire Length Contract",
    "GUI_COPYDATA_WIRE_LENGTH_CONTRACT",
    "Sandboxie/core/svc/GuiWire.h",
    "Sandboxie/core/svc/GuiServer.cpp",
    "COPYDATASTRUCT",
    "FIELD_OFFSET(GUI_SEND_COPYDATA_REQ, cds_buf)",
]:
    require(ledger, term, "combined ledger")

print("SREV-192 schema/source gate passed")
