#!/usr/bin/env python3
import json
from pathlib import Path

from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-233 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-233 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-233-key-driver-header-topology.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-233 failed: schema is not draft-07")
if schema.get("id") != "KEY_DRIVER_HEADER_TOPOLOGY_CONTRACT":
    raise SystemExit("SREV-233 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/drv/key.h":
    raise SystemExit("SREV-233 failed: wrong owner")

official_refs = "\n".join(schema["official_references"])
for term in [
    "registering-for-notifications",
    "filtering-registry-operations-on-application-hives",
    "opening-a-handle-to-a-registry-key-object",
    "object-handles",
]:
    require(official_refs, term, "official reference")

contracts = "\n".join(schema["contracts"])
for term in [
    "driver registry module declaration header",
    "module lifecycle and process entry points",
    "does not own registry filter registration",
    "key.c key_flt.c key_xp.c driver.c or process.c",
    "driver initialization and process lifecycle topology",
]:
    require(contracts, term, "schema contract")

spec = (ROOT / "docs/plan/srev-233-key-driver-header-topology.md").read_text()
header = (ROOT / "Sandboxie/core/drv/key.h").read_text()
key_source = (ROOT / "Sandboxie/core/drv/key.c").read_text()
key_filter = (ROOT / "Sandboxie/core/drv/key_flt.c").read_text()
key_xp = (ROOT / "Sandboxie/core/drv/key_xp.c").read_text()
driver = (ROOT / "Sandboxie/core/drv/driver.c").read_text()
process = (ROOT / "Sandboxie/core/drv/process.c").read_text()
ledger = read_combined_ledger(ROOT)
fragment = (ROOT / "docs/plan/ledger/srev-233.md").read_text()

for term in [
    '#include "driver.h"',
    "BOOLEAN Key_Init(void);",
    "void Key_Unload(void);",
    "BOOLEAN Key_MountHive(PROCESS *proc);",
    "void Key_UnmountHive(PROCESS *proc);",
    "BOOLEAN Key_InitProcess(PROCESS *proc);",
]:
    require(header, term, "header declaration")

for forbidden in [
    "CmRegisterCallbackEx",
    "CmUnRegisterCallback",
    "Key_Mounts",
    "ZwLoadKey",
    "ZwOpenKey",
    "Api_SetFunction",
    "Process_GetPaths",
    "Key_MyParseProc_2",
]:
    reject(header, forbidden, "runtime owner code in header")

for term in [
    '#include "key.h"',
    "static LIST Key_Mounts;",
    "static PERESOURCE Key_MountsLock = NULL;",
    "const WCHAR *Key_Registry_Machine = L\"\\\\REGISTRY\\\\MACHINE\";",
    "Api_SetFunction(API_GET_UNMOUNT_HIVE,   Key_Api_GetUnmountHive);",
    "Api_SetFunction(API_OPEN_KEY,           Key_Api_Open);",
    "Api_SetFunction(API_SET_LOW_LABEL_KEY,  Key_Api_SetLowLabel);",
    "_FX BOOLEAN Key_InitProcess(PROCESS *proc)",
    "_FX NTSTATUS Key_MyParseProc_2(OBJ_PARSE_PROC_ARGS_2)",
    "_FX BOOLEAN Key_MountHive(PROCESS *proc)",
    "_FX void Key_UnmountHive(PROCESS *proc)",
]:
    require(key_source, term, "key.c owner topology")

for term in [
    "static BOOLEAN Key_Init_Filter(void);",
    "static void Key_Unload_Filter(void);",
    "static NTSTATUS Key_Callback(void *Context, void *Arg1, void *Arg2);",
    "MmGetSystemRoutineAddress(&uni)",
    "pCmRegisterCallbackEx(",
    "CmUnRegisterCallback(Key_Cookie);",
    "NotifyEvent != RegNtPreCreateKeyEx",
    "NotifyEvent != RegNtPreOpenKeyEx",
]:
    require(key_filter, term, "registry filter topology")

for term in [
    "static BOOLEAN Key_Init_XpHook(void);",
    "static void Key_Unload_XpHook(void);",
    "static NTSTATUS Key_MyParseProc(OBJ_PARSE_PROC_ARGS);",
    "Key_Check_KB979683(L\"\\\\KB979683\");",
    "Obj_HookParseProc(Key_ObjectName,",
    "CALL_PARSE_PROC_2(Key_MyParseProc_2);",
]:
    require(key_xp, term, "XP parse hook topology")

require(driver, "ok = Key_Init();", "driver initialization caller")
for term in [
    "Key_UnmountHive(proc);",
    "if (!fail && !Key_MountHive(proc))",
    "if (!fail && !Key_InitProcess(proc))",
]:
    require(process, term, "process lifecycle caller")

for term in [
    "SREV-047: Key Low-Label Boxed Path",
    "owner: Sandboxie/core/drv/key.c",
    "SREV-098: IE Embedding CLSID Registry Policy",
    "owner: Sandboxie/core/drv/key_flt.c",
    "SREV-167: XP Key Hotfix Kernel Handle",
    "owner: Sandboxie/core/drv/key_xp.c",
    "SREV-176: Key Utility Registry Path Shape",
    "SREV-227: Driver Registry Path Counted Copy",
]:
    require(ledger, term, "existing registry owner coverage")

for term in [
    "No source patch",
    "declaration/topology header",
    "Microsoft documents registry filtering",
    "under `\\REGISTRY\\A`",
    "concrete-owner SREV Windows",
]:
    require(spec, term, "spec classification")

for term in [
    "kind: srev-ledger-entry",
    "id: SREV-233",
    "owner: Sandboxie/core/drv/key.h",
    "docs-only-source-topology-reviewed",
    "srev-233-key-driver-header-topology.schema.json",
    "check-srev-233.py",
]:
    require(fragment, term, "ledger fragment")
    require(ledger, term, "combined ledger")

print("SREV-233 source gate passed")
