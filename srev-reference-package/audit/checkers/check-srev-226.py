#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-226 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-226 failed: {label} still contains {needle!r}")


def section(text: str, start: str, end: str) -> str:
    start_index = text.index(start)
    end_index = text.index(end, start_index)
    return text[start_index:end_index]


schema = json.loads(
    (ROOT / "docs/plan/srev-226-pstore-enumerator-query-interface-contract.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-226 failed: schema is not draft-07")
if schema.get("id") != "PSTORE_ENUMERATOR_QUERY_INTERFACE_CONTRACT":
    raise SystemExit("SREV-226 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "pstore.h owns the generated COM ABI",
    "local COM enumerator implementations",
    "local IID_IEnumPStoreTypes and IID_IEnumPStoreItems definitions",
    "reject a null ppvObject with E_POINTER",
    "return S_OK only for IID_IUnknown and the concrete enumerator IID",
    "Unsupported IIDs must set ppvObject output to NULL and return E_NOINTERFACE",
    "publish the adjusted COM interface pointer",
    "Successful queries must AddRef",
]:
    require(contracts, term, "schema")

spec = (ROOT / "docs/plan/srev-226-pstore-enumerator-query-interface-contract.md").read_text()
ledger = read_combined_ledger(ROOT)
pstore_h = (ROOT / "Sandboxie/core/dll/pstore.h").read_text()
enum_h = (ROOT / "Sandboxie/core/dll/ipstore_enum.h").read_text()
enum_cpp = (ROOT / "Sandboxie/core/dll/ipstore_enum.cpp").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "EXTERN_C const IID IID_IEnumPStoreItems =\n    { 0x4C83B307, 0x0B70, 0x4726, { 0x8F, 0x75, 0x39, 0x6E, 0xBB, 0xDA, 0xA4, 0x01 } };",
    "EXTERN_C const IID IID_IEnumPStoreTypes =\n    { 0x4C83B307, 0x0B70, 0x4726, { 0x8F, 0x75, 0x39, 0x6E, 0xBB, 0xDA, 0xA4, 0x02 } };",
]:
    require(enum_cpp, term, "ipstore_enum.cpp IID definitions")

for term in [
    "EXTERN_C const IID IID_IEnumPStoreItems;",
    "MIDL_INTERFACE(\"4C83B307-0B70-4726-8F75-396EBBDAA401\")",
    "EXTERN_C const IID IID_IEnumPStoreTypes;",
    "MIDL_INTERFACE(\"4C83B307-0B70-4726-8F75-396EBBDAA402\")",
]:
    require(pstore_h, term, "pstore.h ABI")

for term in [
    "class IEnumPStoreTypesImpl :",
    "public IEnumPStoreGeneric, public IEnumPStoreTypes",
    "class IEnumPStoreItemsImpl :",
    "public IEnumPStoreGeneric, public IEnumPStoreItems",
]:
    require(enum_h, term, "ipstore_enum.h inheritance topology")

types_qi = section(
    enum_cpp,
    "HRESULT IEnumPStoreTypesImpl::QueryInterface",
    "//---------------------------------------------------------------------------\n// IEnumPStoreTypesImpl::AddRef",
)
for term in [
    "if (! ppvObject)\n        return E_POINTER;",
    "IsEqualIID(iid, IID_IUnknown) || IsEqualIID(iid, IID_IEnumPStoreTypes)",
    "*ppvObject = (IEnumPStoreTypes *)this;",
    "*ppvObject = NULL;",
    "return E_NOINTERFACE;",
    "this->AddRef();",
    "return S_OK;",
]:
    require(types_qi, term, "IEnumPStoreTypesImpl QueryInterface")
reject(types_qi, "*ppvObject = this;", "unadjusted type enumerator pointer")
if types_qi.index("this->AddRef();") < types_qi.index("*ppvObject = (IEnumPStoreTypes *)this;"):
    raise SystemExit("SREV-226 failed: type AddRef appears before supported pointer publication")

items_qi = section(
    enum_cpp,
    "HRESULT IEnumPStoreItemsImpl::QueryInterface",
    "//---------------------------------------------------------------------------\n// IEnumPStoreItemsImpl::AddRef",
)
for term in [
    "if (! ppvObject)\n        return E_POINTER;",
    "IsEqualIID(iid, IID_IUnknown) || IsEqualIID(iid, IID_IEnumPStoreItems)",
    "*ppvObject = (IEnumPStoreItems *)this;",
    "*ppvObject = NULL;",
    "return E_NOINTERFACE;",
    "this->AddRef();",
    "return S_OK;",
]:
    require(items_qi, term, "IEnumPStoreItemsImpl QueryInterface")
reject(items_qi, "*ppvObject = this;", "unadjusted item enumerator pointer")
if items_qi.index("this->AddRef();") < items_qi.index("*ppvObject = (IEnumPStoreItems *)this;"):
    raise SystemExit("SREV-226 failed: item AddRef appears before supported pointer publication")

for term in [
    "### SREV-226: PStore Enumerator QueryInterface Contract",
    "PSTORE_ENUMERATOR_QUERY_INTERFACE_CONTRACT",
    "srev-226-pstore-enumerator-query-interface-contract.schema.json",
    "Sandboxie/core/dll/ipstore_enum.cpp",
    "Sandboxie/core/dll/ipstore_enum.h",
    "Sandboxie/core/dll/pstore.h",
    "IID_IEnumPStoreTypes",
    "IID_IEnumPStoreItems",
    "E_NOINTERFACE",
    "E_POINTER",
]:
    require(ledger, term, "ledger")

print("SREV-226 source gate passed")
