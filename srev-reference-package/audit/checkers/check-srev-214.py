#!/usr/bin/env python3
import json
from pathlib import Path

from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-214 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-214 failed: stale {label} remains {needle!r}")


def between(text: str, start: str, end: str) -> str:
    a = text.index(start)
    b = text.index(end, a + len(start))
    return text[a:b]


schema = json.loads(
    (ROOT / "docs/plan/srev-214-driver-dll-entry-resource-lifetime.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-214 failed: schema is not draft-07")
if schema.get("id") != "DRIVER_DLL_ENTRY_RESOURCE_LIFETIME":
    raise SystemExit("SREV-214 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/drv/dll.c":
    raise SystemExit("SREV-214 failed: wrong owner")
if schema.get("declaration") != "Sandboxie/core/drv/dll.h":
    raise SystemExit("SREV-214 failed: wrong declaration")

contracts = "\n".join(schema["contracts"])
for term in [
    "driver-side DLL image load entries",
    "mapped view",
    "section handle",
    "file handle",
    "pool allocation",
    "before returning NULL",
    "Dll_List",
    "OBJ_KERNEL_HANDLE",
]:
    require(contracts, term, "schema contract")

spec = (ROOT / "docs/plan/srev-214-driver-dll-entry-resource-lifetime.md").read_text()
dll = (ROOT / "Sandboxie/core/drv/dll.c").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-214.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

require(dll, "static void Dll_FreeEntry(DLL_ENTRY *dll);", "free helper declaration")
free_entry = between(
    dll,
    "_FX void Dll_FreeEntry(DLL_ENTRY *dll)",
    "//---------------------------------------------------------------------------\n// Dll_Load",
)
for term in [
    "if (! dll)\n        return;",
    "if (dll->base)\n        ZwUnmapViewOfSection(NtCurrentProcess(), dll->base);",
    "if (dll->hSection)\n        ZwClose(dll->hSection);",
    "if (dll->hFile)\n        ZwClose(dll->hFile);",
    "Mem_Free(dll, sizeof(DLL_ENTRY));",
]:
    require(free_entry, term, "free helper ownership")

unload = between(
    dll,
    "_FX void Dll_Unload(void)",
    "//---------------------------------------------------------------------------\n// Dll_FreeEntry",
)
require(unload, "List_Remove(&Dll_List, dll);", "unload list removal")
require(unload, "Dll_FreeEntry(dll);", "unload entry release")
reject(unload, "ZwUnmapViewOfSection", "unload inline view release")
reject(unload, "ZwClose(dll->hSection)", "unload inline section close")
reject(unload, "ZwClose(dll->hFile)", "unload inline file close")

load = between(
    dll,
    "_FX DLL_ENTRY *Dll_Load(const WCHAR *DllBaseName)",
    "//---------------------------------------------------------------------------\n// Dll_RvaToAddr",
)
for term in [
    "InitializeObjectAttributes(\n        &objattrs, &uni, OBJ_CASE_INSENSITIVE | OBJ_KERNEL_HANDLE, NULL, NULL);",
    "status = ZwCreateFile(",
    "status = ZwCreateSection(",
    "status = ZwMapViewOfSection(",
    "List_Insert_After(&Dll_List, NULL, dll);",
    "Dll_FreeEntry(dll);\n        dll = NULL;",
]:
    require(load, term, "load lifetime topology")
reject(load, "&objattrs, &uni, OBJ_CASE_INSENSITIVE, NULL, NULL);", "non-kernel object attributes")
reject(load, "Log_Status_Ex(MSG_DLL_LOAD, err, status, DllBaseName);\n        dll = NULL;", "failure without cleanup")

for term in [
    "kind: srev-ledger-entry",
    "id: SREV-214",
    "owner: Sandboxie/core/drv/dll.c",
    "declaration: Sandboxie/core/drv/dll.h",
    "spec: docs/plan/srev-214-driver-dll-entry-resource-lifetime.md",
    "schema: docs/plan/srev-214-driver-dll-entry-resource-lifetime.schema.json",
    "checker: docs/plan/check-srev-214.py",
    "patched source-level after official object-handle and section-view lifetime review",
]:
    require(ledger_fragment, term, "ledger fragment")
    require(ledger, term, "combined ledger")

print("SREV-214 source gate passed")
