#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-043 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-043 failed: {label} still contains {needle!r}")


schema = json.loads((ROOT / "docs/plan/srev-043-dynamic-port-fixed-string.schema.json").read_text())
if schema.get("id") != "DYNAMIC_PORT_FIXED_STRING":
    raise SystemExit("SREV-043 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "port_name is required",
    "DYNAMIC_PORT_NAME_CHARS WCHARs",
    "NUL-terminated before DYNAMIC_PORT_NAME_CHARS - 1",
    "NUL-terminated before DYNAMIC_PORT_ID_CHARS - 1",
    "must not be truncated",
    "Ipc_CreateDynamicPort receives only local fixed buffers",
]:
    require(contracts, term, "schema")

src = (ROOT / "Sandboxie/core/drv/ipc_port.c").read_text()
spec = (ROOT / "docs/plan/srev-043-dynamic-port-fixed-string.md").read_text()
ledger = read_combined_ledger(ROOT)

start = src.index("_FX NTSTATUS Ipc_Api_OpenDynamicPort(")
end = src.index("// Ipc_CheckPortRequest_Dynamic", start)
open_dynamic = src[start:end]

for term in [
    "static NTSTATUS Ipc_CopyFixedUserWString(",
    "wmemzero(dst, chars);",
    "if (! src)",
    "ProbeForRead((WCHAR *)src, sizeof(WCHAR) * chars, sizeof(WCHAR));",
    "for (i = 0; i < chars - 1; ++i)",
    "if (src[i] == L'\\0')",
    "dst[i] = src[i];",
    "if ((! i) || (i == chars - 1))",
]:
    require(src, term, "fixed string helper")

for term in [
    "status = Ipc_CopyFixedUserWString(\n            portName, pArgs->port_name.val, DYNAMIC_PORT_NAME_CHARS);",
    "status = Ipc_CopyFixedUserWString(\n            portId, pArgs->port_id.val, DYNAMIC_PORT_ID_CHARS);",
    "Ipc_CreateDynamicPort(\n            portId, portName",
    "Process_AddPath(proc, &proc->open_ipc_paths, NULL, FALSE, portName, FALSE);",
]:
    require(open_dynamic, term, "Ipc_Api_OpenDynamicPort")

for term in [
    "wmemcpy(portName, pArgs->port_name.val, DYNAMIC_PORT_NAME_CHARS - 1)",
    "wmemcpy(portId, pArgs->port_id.val, DYNAMIC_PORT_ID_CHARS - 1)",
]:
    reject(open_dynamic, term, "Ipc_Api_OpenDynamicPort")

for term in [
    "https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-probeforread",
    "srev-043-dynamic-port-fixed-string.schema.json",
]:
    require(spec, term, "spec")

for term in [
    "### SREV-043: Dynamic Port Fixed String",
    "Ipc_CopyFixedUserWString",
    "srev-043-dynamic-port-fixed-string.schema.json",
]:
    require(ledger, term, "ledger")

print("SREV-043 schema/source gate passed")
