#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-020 failed: {label} missing {needle!r}")


schema = json.loads((ROOT / "docs/plan/srev-020-getfilename-type-output-abi.schema.json").read_text())
if schema.get("id") != "GETFILENAME_TYPE_OUTPUT_ABI_SHAPE":
    raise SystemExit("SREV-020 failed: schema missing GETFILENAME_TYPE_OUTPUT_ABI_SHAPE")

drv = (ROOT / "Sandboxie/core/drv/file.c").read_text()
api_h = (ROOT / "Sandboxie/core/dll/sbieapi.h").read_text()
api_c = (ROOT / "Sandboxie/core/dll/sbieapi.c").read_text()
spec = (ROOT / "docs/plan/srev-020-getfilename-type-output-abi.md").read_text()
ledger = read_combined_ledger(ROOT)

if "memcpy(type_buf" in drv:
    raise SystemExit("SREV-020 failed: driver still writes an unbounded type_buf string")

for term in ["type_buf = args->type_buf.val", "STATUS_INVALID_PARAMETER", "__leave"]:
    require(drv, term, "driver source")

if "ObjTypeReserved" not in api_h and "ObjTypeReserved" not in api_c:
    raise SystemExit("SREV-020 failed: ObjTypeReserved not exposed via sbieapi header or impl")

type_pos = drv.find("type_buf = args->type_buf.val;")
invalid_pos = drv.find("status = STATUS_INVALID_PARAMETER;", type_pos)
name_pos = drv.find("name_buf = args->name_buf.val;", type_pos)
if min(type_pos, invalid_pos, name_pos) < 0 or not (type_pos < invalid_pos < name_pos):
    raise SystemExit("SREV-020 failed: type_buf must be rejected before name output")

for term in ["METHOD_NEITHER", "ProbeForWrite", "STATUS_INVALID_PARAMETER"]:
    require(spec, term, "spec")

require(ledger, "### SREV-020: Driver GetFileName Object-Type Output Has ABI Shape Mismatch", "ledger")
require(ledger, "Sandboxie/core/drv/file.c", "ledger")

print("SREV-020 schema/source gate passed")
