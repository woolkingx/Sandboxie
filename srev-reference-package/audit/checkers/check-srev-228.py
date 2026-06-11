#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-228 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-228 failed: {label} still contains {needle!r}")


def section(text: str, start: str, end: str) -> str:
    start_index = text.index(start)
    end_index = text.index(end, start_index)
    return text[start_index:end_index]


schema = json.loads(
    (ROOT / "docs/plan/srev-228-taskbar-property-store-query-interface.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-228 failed: schema is not draft-07")
if schema.get("id") != "TASKBAR_PROPERTY_STORE_QUERY_INTERFACE_CONTRACT":
    raise SystemExit("SREV-228 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "propsys.h is the local Vista 7 SDK shim for the IPropertyStore ABI",
    "taskbar.c owns the Sandboxie wrapper returned from SHGetPropertyStoreForWindow",
    "IPropertyStore inherits from IUnknown",
    "reject a null output pointer with E_POINTER",
    "Unsupported IIDs must set ppv output to NULL and return E_NOINTERFACE",
    "publish the supported interface pointer and then AddRef it",
]:
    require(contracts, term, "schema")

spec = (ROOT / "docs/plan/srev-228-taskbar-property-store-query-interface.md").read_text()
ledger = read_combined_ledger(ROOT)
propsys_h = (ROOT / "Sandboxie/core/dll/propsys.h").read_text()
taskbar_c = (ROOT / "Sandboxie/core/dll/taskbar.c").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "typedef interface IPropertyStore IPropertyStore;",
    "HRESULT ( STDMETHODCALLTYPE *QueryInterface )(",
    "HRESULT ( STDMETHODCALLTYPE *SetValue )(",
    "HRESULT ( STDMETHODCALLTYPE *Commit )(",
    "DEFINE_PROPERTYKEY(PKEY_AppUserModel_ID",
]:
    require(propsys_h, term, "propsys.h ABI shim")

for term in [
    "static const GUID IID_IPropertyStore",
    "0x886D8EEB, 0x8CF2, 0x4446",
    "static const GUID Taskbar_IID_IUnknown",
    "0x00000000, 0x0000, 0x0000",
    "SHGetPropertyStoreForWindow",
]:
    require(taskbar_c, term, "taskbar constants/topology")

query_interface = section(
    taskbar_c,
    "_FX HRESULT Taskbar_Unknown_QueryInterface",
    "//---------------------------------------------------------------------------\n// Taskbar_Unknown_AddRef",
)
for term in [
    "if (! ppv)\n        return E_POINTER;",
    "memcmp(riid, &Taskbar_IID_IUnknown, sizeof(GUID)) != 0 &&",
    "memcmp(riid, &IID_IPropertyStore, sizeof(GUID)) != 0",
    "*ppv = NULL;",
    "return E_NOINTERFACE;",
    "*ppv = This;",
    "This->lpVtbl->AddRef(This);",
    "return S_OK;",
]:
    require(query_interface, term, "Taskbar QueryInterface source shape")
reject(query_interface, "This->lpVtbl->AddRef(This);\n    *ppv = This;", "old AddRef-before-output shape")
if query_interface.index("*ppv = This;") > query_interface.index("This->lpVtbl->AddRef(This);"):
    raise SystemExit("SREV-228 failed: AddRef appears before successful pointer publication")

wrapper = section(
    taskbar_c,
    "HRESULT Taskbar_SHGetPropertyStoreForWindow",
    "//---------------------------------------------------------------------------\n// Taskbar_IPropertyStore_GetCount",
)
for term in [
    "__sys_SHGetPropertyStoreForWindow(hwnd, riid, ppv)",
    "memcmp(riid, &IID_IPropertyStore, sizeof(GUID)) != 0",
    "pMyStore = Taskbar_AllocUnknown(5, *(IUnknown **)ppv);",
    "*(IPropertyStore **)ppv = (IPropertyStore *)pMyStore;",
]:
    require(wrapper, term, "property store wrapper topology")

for term in [
    "### SREV-228: Taskbar Property Store QueryInterface Contract",
    "TASKBAR_PROPERTY_STORE_QUERY_INTERFACE_CONTRACT",
    "srev-228-taskbar-property-store-query-interface.schema.json",
    "Sandboxie/core/dll/propsys.h",
    "Sandboxie/core/dll/taskbar.c",
    "Taskbar_IID_IUnknown",
    "Taskbar_Unknown_QueryInterface",
    "IID_IPropertyStore",
    "E_POINTER",
    "E_NOINTERFACE",
]:
    require(ledger, term, "ledger")

print("SREV-228 source gate passed")
