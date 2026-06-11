#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-161 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-161 failed: {label} still contains {needle!r}")


def section(text: str, start: str, end: str) -> str:
    start_index = text.index(start)
    end_index = text.index(end, start_index)
    return text[start_index:end_index]


schema = json.loads(
    (ROOT / "docs/plan/srev-161-pstore-enumerator-end-contract.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-161 failed: schema is not draft-07")
if schema.get("id") != "PSTORE_ENUMERATOR_END_CONTRACT":
    raise SystemExit("SREV-161 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "pstore.h is the ABI/schema evidence for the PStore COM interfaces",
    "pstoreserver.cpp owns the service-side PStore enumeration broker",
    "successful factory calls must produce non-null enumerator interface pointers",
    "Next(1, ..., &fetched) yields exactly one item only when hr == S_OK and fetched == 1",
    "S_FALSE local ERROR_NO_MORE_ITEMS or any successful result with fetched == 0 is end-of-enumeration not another item",
    "end-of-enumeration is normalized to S_OK in the Sandboxie reply after all fetched items have been copied",
    "unexpected successful Next result with neither one fetched item nor a recognized end shape fails as E_UNEXPECTED",
    "EnumTypes returns the LONG_REPLY packet pointer not an HRESULT value",
    "does not change PStore read write policy current-user versus local-machine lookup order wire struct layout prompt suppression or local sandboxed PStore merge behavior",
    "Linux source gate is not Windows runtime proof",
]:
    require(contracts, term, "schema")

pstore_header = (ROOT / "Sandboxie/core/dll/pstore.h").read_text()
wire = (ROOT / "Sandboxie/core/svc/pstorewire.h").read_text()
source = (ROOT / "Sandboxie/core/svc/pstoreserver.cpp").read_text()
spec = (ROOT / "docs/plan/srev-161-pstore-enumerator-end-contract.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-161.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "/* this ALWAYS GENERATED file contains the definitions for the interfaces */",
    "IEnumPStoreItems",
    "IEnumPStoreTypes",
    "virtual HRESULT STDMETHODCALLTYPE EnumTypes(",
    "virtual HRESULT STDMETHODCALLTYPE EnumSubtypes(",
    "virtual HRESULT STDMETHODCALLTYPE EnumItems(",
    "virtual HRESULT STDMETHODCALLTYPE Next(",
    "DWORD *pceltFetched",
]:
    require(pstore_header, term, "pstore.h ABI")

for term in [
    "struct tagPSTORE_ENUM_TYPES_RPL",
    "ULONG count;",
    "GUID guids[1];",
    "struct tagPSTORE_ENUM_ITEMS_RPL",
    "WCHAR names[1];",
]:
    require(wire, term, "PStoreWire")

helper = section(source, "static BOOLEAN PStore_IsEnumEnd", "//---------------------------------------------------------------------------\n// Constructor")
for term in [
    "hr == S_FALSE",
    "hr == HRESULT_FROM_WIN32(ERROR_NO_MORE_ITEMS)",
    "SUCCEEDED(hr) && fetched == 0",
]:
    require(helper, term, "PStore_IsEnumEnd")

enum_types = section(source, "MSG_HEADER *PStoreServer::EnumTypes", "//---------------------------------------------------------------------------\n// EnumItems")
for term in [
    "if (SUCCEEDED(hr) && (! pEnum))\n            hr = E_POINTER;",
    "while (SUCCEEDED(hr)) {",
    "n = 0;",
    "hr = pEnum->Next(1, &guid, &n);",
    "if (hr == S_OK && n == 1) {",
    "if (PStore_IsEnumEnd(hr, n)) {",
    "hr = S_OK;",
    "hr = E_UNEXPECTED;",
    "rpl->count = 0;",
    "hr = pEnum->Next(count, rpl->guids, &n);",
    "rpl->count = n;",
    "rpl->h.status = S_OK;",
    "return (MSG_HEADER *)rpl;",
]:
    require(enum_types, term, "EnumTypes")
reject(enum_types, "return S_OK;", "EnumTypes HRESULT return")
reject(enum_types, "while (SUCCEEDED(hr)) {\n            hr = pEnum->Next", "EnumTypes uncounted Next loop")
if enum_types.index("if (SUCCEEDED(hr) && (! pEnum))") > enum_types.index("hr = pEnum->Next(1, &guid, &n);"):
    raise SystemExit("SREV-161 failed: EnumTypes pEnum null gate is after Next")

enum_items = source[source.index("MSG_HEADER *PStoreServer::EnumItems"):]
for term in [
    "if (SUCCEEDED(hr) && (! pEnum))\n            hr = E_POINTER;",
    "while (SUCCEEDED(hr)) {",
    "name = NULL;",
    "n = 0;",
    "hr = pEnum->Next(1, &name, &n);",
    "if (hr == S_OK && n == 1 && name) {",
    "CoTaskMemFree(name);",
    "if (PStore_IsEnumEnd(hr, n)) {",
    "hr = S_OK;",
    "hr = E_UNEXPECTED;",
    "rpl->h.status = S_OK;",
]:
    require(enum_items, term, "EnumItems")
reject(enum_items, "if (SUCCEEDED(hr)) {\n                wcscpy", "EnumItems S_FALSE copy path")
if enum_items.index("if (SUCCEEDED(hr) && (! pEnum))") > enum_items.index("hr = pEnum->Next(1, &name, &n);"):
    raise SystemExit("SREV-161 failed: EnumItems pEnum null gate is after Next")

for term in [
    "### SREV-161: PStore Enumerator End Contract",
    "PSTORE_ENUMERATOR_END_CONTRACT",
    "srev-161-pstore-enumerator-end-contract.schema.json",
    "Sandboxie/core/dll/pstore.h",
    "Sandboxie/core/svc/pstoreserver.cpp",
    "PStore_IsEnumEnd",
    "S_FALSE",
    "ERROR_NO_MORE_ITEMS",
    "E_UNEXPECTED",
    "return (MSG_HEADER *)rpl;",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-161 schema/source gate passed")
