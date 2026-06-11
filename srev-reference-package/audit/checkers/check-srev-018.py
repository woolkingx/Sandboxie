#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-018 failed: {label} missing {needle!r}")


schema = json.loads((ROOT / "docs/plan/srev-018-dynamic-rpc-port-policy.schema.json").read_text())
if schema.get("id") != "DYNAMIC_RPC_PORT_POLICY_SHAPE":
    raise SystemExit("SREV-018 failed: schema missing DYNAMIC_RPC_PORT_POLICY_SHAPE")

src = (ROOT / "Sandboxie/core/drv/ipc_port.c").read_text()
spec = (ROOT / "docs/plan/srev-018-dynamic-rpc-port-policy.md").read_text()
ledger = read_combined_ledger(ROOT)

for term in [
    "Ipc_DynamicPortSize",
    "Ipc_CreateDynamicPort",
    "List_Insert_After(&Ipc_Dynamic_Ports.Ports, port, new_port)",
    "List_Remove(&Ipc_Dynamic_Ports.Ports, port)",
    "Mem_Free(port, Ipc_DynamicPortSize(port->FilterCount))",
    "Ipc_Dynamic_Ports.pSpoolerPort = new_port",
]:
    require(src, term, "driver source")

if "wmemcpy(port->wstrPortName, portName, DYNAMIC_PORT_NAME_CHARS);" in src:
    raise SystemExit("SREV-018 failed: existing entry still refreshes name only")

create = src.find("new_port = Ipc_CreateDynamicPort")
lock = src.find("ExAcquireResourceExclusiveLite(Ipc_Dynamic_Ports.pPortLock")
if min(create, lock) < 0 or not create < lock:
    raise SystemExit("SREV-018 failed: replacement entry must be built before publication lock")

probe = src.find("ProbeForRead(FilterIDs")
publish = src.find("List_Insert_After(&Ipc_Dynamic_Ports.Ports, port, new_port)")
if min(probe, publish) < 0 or not probe < publish:
    raise SystemExit("SREV-018 failed: filter payload must be probed before publish")

for term in ["RpcEpRegister", "FilterIDs", "re-register"]:
    require(spec, term, "spec")

require(ledger, "### SREV-018: Dynamic RPC Port Re-Registration Leaves Existing Filter IDs Stale", "ledger")
require(ledger, "Sandboxie/core/drv/ipc", "ledger")

print("SREV-018 schema/source gate passed")
