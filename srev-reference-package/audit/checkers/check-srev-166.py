#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-166 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-166 failed: {label} still contains {needle!r}")


def section(text: str, start: str, end: str) -> str:
    start_index = text.index(start)
    end_index = text.index(end, start_index)
    return text[start_index:end_index]


schema = json.loads((ROOT / "docs/plan/srev-166-com-classfactory-createinstance-hr.schema.json").read_text())
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-166 failed: schema is not draft-07")
if schema.get("id") != "COM_CLASSFACTORY_CREATEINSTANCE_HRESULT":
    raise SystemExit("SREV-166 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "comserver9.c owns the simulated COM class factory implementation",
    "CreateInstance must return E_POINTER for a null output pointer",
    "CreateInstance must return CLASS_E_NOAGGREGATION when pUnkOuter is non-NULL",
    "if pMyCreateInstance cannot create a matching object CreateInstance must return E_NOINTERFACE",
    "if IUnknown_QueryInterface fails for riid CreateInstance must return that failure HRESULT and leave ppvObject null",
    "S_OK is legal only when the requested interface pointer is returned",
    "Linux source gate is not Windows COM activation runtime proof",
]:
    require(contracts, term, "schema")

source = (ROOT / "Sandboxie/core/svc/comserver9.c").read_text()
spec = (ROOT / "docs/plan/srev-166-com-classfactory-createinstance-hr.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-166.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

create_instance = section(
    source,
    "_FX HRESULT ComServer_IClassFactory_CreateInstance(",
    "//---------------------------------------------------------------------------\n// ComServer_IClassFactory_LockServer",
)
for term in [
    "HRESULT hr;",
    "if (! ppvObject)",
    "return E_POINTER;",
    "if (pUnkOuter) {",
    "*ppvObject = NULL;",
    "return CLASS_E_NOAGGREGATION;",
    "obj = (IUnknown *)(((IMyClassFactory *)This)->pMyCreateInstance(riid));",
    "hr = IUnknown_QueryInterface(obj, riid, ppvObject);",
    "hr = E_NOINTERFACE;",
    "return hr;",
]:
    require(create_instance, term, "CreateInstance")
reject(create_instance, "return S_OK;", "unconditional success return")

for term in [
    "### SREV-166: COM ClassFactory CreateInstance HRESULT",
    "COM_CLASSFACTORY_CREATEINSTANCE_HRESULT",
    "srev-166-com-classfactory-createinstance-hr.schema.json",
    "Sandboxie/core/svc/comserver9.c",
    "ComServer_IClassFactory_CreateInstance",
    "IClassFactory::CreateInstance",
    "IUnknown_QueryInterface",
    "returns `hr`",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-166 schema/source gate passed")
