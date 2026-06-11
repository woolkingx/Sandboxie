#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-005 failed: {label} missing {needle!r}")


schema = json.loads((ROOT / "docs/plan/srev-005-portrequest-message-header-spec.schema.json").read_text())
if schema.get("id") != "PORTREQUEST_MESSAGE_HEADER_SHAPE":
    raise SystemExit("SREV-005 failed: schema missing PORTREQUEST_MESSAGE_HEADER_SHAPE")

contracts = "\n".join(schema["contracts"])
for term in [
    "PORT_MESSAGE carries u1.s1.DataLength",
    "MSG_HEADER is two ULONGs",
    "compare DataLength against sizeof(MSG_HEADER) before touching msg_Data",
]:
    require(contracts, term, "schema contracts")

src = (ROOT / "Sandboxie/core/svc/PipeServer.cpp").read_text()
spec = (ROOT / "docs/plan/srev-005-portrequest-message-header-spec.md").read_text()
ledger = read_combined_ledger(ROOT)

lines = src.splitlines()
def first_line(needle: str) -> int:
    for i, line in enumerate(lines, 1):
        if needle in line:
            return i
    return -1

gate = first_line("DataLength < sizeof(MSG_HEADER)")
read = first_line("ULONG *msg_Data = (ULONG *)msg->Data")
call = first_line("CallTarget(client->buf_hdr")
if min(gate, read, call) < 0:
    raise SystemExit("SREV-005 failed: missing gate, header read, or CallTarget marker")
if not (gate < read < call):
    raise SystemExit("SREV-005 failed: MSG_HEADER length gate must precede msg_Data read and CallTarget")

require(src, "buf_len >= sizeof(MSG_HEADER)", "service source")

for term in ["!lpc", "ALPC ETW", "sizeof(MSG_HEADER)"]:
    require(spec, term, "spec")

require(ledger, "### SREV-005: SbieSvc PortRequest Reads Message ID Before Minimum Header Check", "ledger")
require(ledger, "Sandboxie/core/svc/PipeServer.cpp", "ledger")

print("SREV-005 schema/source gate passed")
