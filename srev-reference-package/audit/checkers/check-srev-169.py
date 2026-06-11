#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-169 failed: {label} missing {needle!r}")


def section(text: str, start: str, end: str) -> str:
    start_index = text.index(start)
    end_index = text.index(end, start_index)
    return text[start_index:end_index]


schema = json.loads((ROOT / "docs/plan/srev-169-ipc-unload-list-resources.schema.json").read_text())
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-169 failed: schema is not draft-07")
if schema.get("id") != "IPC_UNLOAD_LIST_RESOURCES":
    raise SystemExit("SREV-169 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "ipc.h owns the IPC_DYNAMIC_PORT and IPC_DYNAMIC_PORTS data shape",
    "ipc_port.c may allocate dynamic port nodes and insert them under Ipc_Dynamic_Ports.pPortLock",
    "Ipc_Unload must free dynamic port list nodes before freeing Ipc_Dynamic_Ports.pPortLock",
    "dynamic port unload must acquire pPortLock exclusively inside a critical region",
    "dynamic port unload must clear pSpoolerPort after draining the list",
    "Ipc_Unload must close each Ipc_ObjDirs handle and free each DIR_OBJ_HANDLE node before freeing Ipc_DirLock",
    "Linux source gate is not Windows driver unload runtime proof",
]:
    require(contracts, term, "schema")

ipc_h = (ROOT / "Sandboxie/core/drv/ipc.h").read_text()
ipc_c = (ROOT / "Sandboxie/core/drv/ipc.c").read_text()
ipc_port_c = (ROOT / "Sandboxie/core/drv/ipc_port.c").read_text()
spec = (ROOT / "docs/plan/srev-169-ipc-unload-list-resources.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-169.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "typedef struct _IPC_DYNAMIC_PORT",
    "UCHAR       FilterIDs[0];",
    "typedef struct _IPC_DYNAMIC_PORTS",
    "PERESOURCE  pPortLock;",
    "LIST        Ports;",
    "IPC_DYNAMIC_PORT*  pSpoolerPort;",
]:
    require(ipc_h, term, "ipc.h dynamic port owner shape")

for term in [
    "port = Mem_AllocEx(Driver_Pool, port_len, TRUE);",
    "List_Insert_After(&Ipc_Dynamic_Ports.Ports, NULL, new_port);",
    "Mem_Free(port, Ipc_DynamicPortSize(port->FilterCount));",
]:
    require(ipc_port_c, term, "ipc_port.c allocation/replacement shape")

unload = ipc_c[ipc_c.index("_FX void Ipc_Unload(void)"):]
for term in [
    "if (Ipc_Dynamic_Ports.pPortLock) {",
    "KeEnterCriticalRegion();",
    "ExAcquireResourceExclusiveLite(Ipc_Dynamic_Ports.pPortLock, TRUE);",
    "IPC_DYNAMIC_PORT *port = List_Head(&Ipc_Dynamic_Ports.Ports);",
    "IPC_DYNAMIC_PORT *next_port = List_Next(port);",
    "ULONG port_len = sizeof(IPC_DYNAMIC_PORT)",
    "sizeof(UCHAR) * port->FilterCount;",
    "List_Remove(&Ipc_Dynamic_Ports.Ports, port);",
    "Mem_Free(port, port_len);",
    "Ipc_Dynamic_Ports.pSpoolerPort = NULL;",
    "ExReleaseResourceLite(Ipc_Dynamic_Ports.pPortLock);",
    "KeLeaveCriticalRegion();",
    "Mem_FreeLockResource(&Ipc_Dynamic_Ports.pPortLock);",
    "DIR_OBJ_HANDLE* next_obj_handle = List_Next(obj_handle);",
    "ZwClose(obj_handle->handle);",
    "List_Remove(&Ipc_ObjDirs, obj_handle);",
    "Mem_Free(obj_handle, sizeof(DIR_OBJ_HANDLE));",
    "Mem_FreeLockResource(&Ipc_DirLock);",
]:
    require(unload, term, "Ipc_Unload")

for term in [
    "### SREV-169: IPC Unload List Resources",
    "IPC_UNLOAD_LIST_RESOURCES",
    "srev-169-ipc-unload-list-resources.schema.json",
    "Sandboxie/core/drv/ipc.h",
    "Sandboxie/core/drv/ipc.c",
    "Sandboxie/core/drv/ipc_port.c",
    "IPC_DYNAMIC_PORTS",
    "Ipc_Unload",
    "Ipc_Dynamic_Ports.pPortLock",
    "DIR_OBJ_HANDLE",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-169 schema/source gate passed")
