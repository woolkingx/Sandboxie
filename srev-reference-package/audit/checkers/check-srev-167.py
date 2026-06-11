#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-167 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-167 failed: {label} still contains {needle!r}")


def section(text: str, start: str, end: str) -> str:
    start_index = text.index(start)
    end_index = text.index(end, start_index)
    return text[start_index:end_index]


schema = json.loads((ROOT / "docs/plan/srev-167-xp-key-hotfix-kernel-handle.schema.json").read_text())
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-167 failed: schema is not draft-07")
if schema.get("id") != "XP_KEY_HOTFIX_KERNEL_HANDLE":
    raise SystemExit("SREV-167 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "key_xp.c owns the legacy XP key parse-procedure hook and its hotfix probe",
    "Key_Check_KB979683 opens registry-key and catalog-file handles only for driver-private hotfix detection",
    "driver-private handles opened through ZwOpenKey or ZwCreateFile must use object attributes with OBJ_KERNEL_HANDLE",
    "the path remains case-insensitive",
    "successful key or file probe handles remain closed by ZwClose",
    "Linux source gate is not Windows XP or Windows 2003 runtime proof",
]:
    require(contracts, term, "schema")

key_xp = (ROOT / "Sandboxie/core/drv/key_xp.c").read_text()
key_c = (ROOT / "Sandboxie/core/drv/key.c").read_text()
obj_h = (ROOT / "Sandboxie/core/drv/obj.h").read_text()
spec = (ROOT / "docs/plan/srev-167-xp-key-hotfix-kernel-handle.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-167.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "#include \"key_xp.c\"",
    "p_Key_Init_2 = Key_Init_XpHook;",
    "p_Key_Unload_2 = Key_Unload_XpHook;",
]:
    require(key_c, term, "key.c XP include/dispatch")

for term in [
    "OBJ_PARSE_PROC_ARGS",
    "OBJ_CALL_SYSTEM_PARSE_PROC",
    "CALL_PARSE_PROC_2",
]:
    require(obj_h, term, "obj.h parse-procedure shape")

probe = section(
    key_xp,
    "_FX void Key_Check_KB979683(const WCHAR *KbName)",
    "//---------------------------------------------------------------------------\n// Key_Init_XpHook",
)
for term in [
    "InitializeObjectAttributes(",
    "OBJ_CASE_INSENSITIVE | OBJ_KERNEL_HANDLE",
    "status = ZwOpenKey(&handle, KEY_READ, &objattrs);",
    "status = ZwCreateFile(",
    "if (NT_SUCCESS(status)) {",
    "ZwClose(handle);",
    "Key_Have_KB979683 = TRUE;",
]:
    require(probe, term, "Key_Check_KB979683")
reject(probe, "&objattrs, &objname, OBJ_CASE_INSENSITIVE, NULL, NULL);", "old non-kernel handle attributes")

for term in [
    "Obj_HookParseProc(Key_ObjectName",
    "Key_MyParseProc",
    "Process_DisableHookEntry(Key_JumpStub);",
    "Key_HookWaitForSingleObject();",
]:
    require(key_xp, term, "XP hook topology")

for term in [
    "### SREV-167: XP Key Hotfix Kernel Handle",
    "XP_KEY_HOTFIX_KERNEL_HANDLE",
    "srev-167-xp-key-hotfix-kernel-handle.schema.json",
    "Sandboxie/core/drv/key_xp.c",
    "Key_Check_KB979683",
    "OBJ_CASE_INSENSITIVE | OBJ_KERNEL_HANDLE",
    "ZwOpenKey",
    "ZwCreateFile",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-167 schema/source gate passed")
