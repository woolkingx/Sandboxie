#!/usr/bin/env python3
import json
from pathlib import Path

from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-243 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-243 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-243-sboxdll-def-legacy-stub.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-243 failed: schema is not draft-07")
if schema.get("id") != "SBOXDLL_DEF_LEGACY_STUB_CONTRACT":
    raise SystemExit("SREV-243 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/dll/SboxDll.def":
    raise SystemExit("SREV-243 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "legacy DEF preprocessor stub not the active linker export table",
    "active Win32 export table is SboxDll32.def",
    "active x64 ARM64EC and ARM64 export table is SboxDll64.def",
    "included sbiedll.def target is absent",
    "Export ABI behavior changes must target SboxDll32.def / SboxDll64.def and SREV-136",
    "project cleanup decision",
]:
    require(contracts, term, "schema contract")

spec = (ROOT / "docs/plan/srev-243-sboxdll-def-legacy-stub.md").read_text()
stub = (ROOT / "Sandboxie/core/dll/SboxDll.def").read_text()
sbox32 = (ROOT / "Sandboxie/core/dll/SboxDll32.def").read_text()
sbox64 = (ROOT / "Sandboxie/core/dll/SboxDll64.def").read_text()
vcxproj = (ROOT / "Sandboxie/core/dll/SboxDll.vcxproj").read_text()
filters = (ROOT / "Sandboxie/core/dll/SboxDll.vcxproj.filters").read_text()
srev136 = (ROOT / "docs/plan/srev-136-sboxdll32-def-export-abi-contract.md").read_text()
ledger = read_combined_ledger(ROOT)
fragment = (ROOT / "docs/plan/ledger/srev-243.md").read_text()

for term in [
    "LIBRARY SboxDll",
    "#define SBIEDLL_LIBRARY_STATEMENT_ISSUED",
    '#include "sbiedll.def"',
]:
    require(stub, term, "legacy stub source")

reject(stub, "EXPORTS", "active export table in stub")
if (ROOT / "Sandboxie/core/dll/sbiedll.def").exists():
    raise SystemExit("SREV-243 failed: sbiedll.def unexpectedly exists")

for term in [
    "<ModuleDefinitionFile>SboxDll32.def</ModuleDefinitionFile>",
    "<ModuleDefinitionFile>SboxDll64.def</ModuleDefinitionFile>",
    '<None Include="SboxDll32.def" />',
    '<None Include="SboxDll64.def" />',
]:
    require(vcxproj, term, "active DEF project topology")

reject(vcxproj, "<ModuleDefinitionFile>SboxDll.def</ModuleDefinitionFile>", "stub ModuleDefinitionFile")
reject(vcxproj, '<None Include="SboxDll.def"', "stub project item")

for term in [
    '<None Include="SboxDll32.def">',
    '<None Include="SboxDll64.def">',
]:
    require(filters, term, "active DEF filters topology")
reject(filters, '<None Include="SboxDll.def"', "stub filters item")

for term in [
    "EXPORTS",
    "Dll_Ordinal1 @1 NONAME",
]:
    require(sbox32, term, "SboxDll32 active export table")
    require(sbox64, term, "SboxDll64 active export table")

for term in [
    "Microsoft documents module-definition files as linker input",
    "SboxDll32.def",
    "SboxDll64.def",
    "ModuleDefinitionFile",
    "dumpbin /exports",
]:
    require(srev136, term, "SREV-136 export ABI owner")

for term in [
    "SREV-136: SboxDll32 DEF Export ABI Contract",
    "owner: Sandboxie/core/dll/SboxDll32.def",
    "SboxDll64.def",
]:
    require(ledger, term, "existing active DEF owner coverage")

for term in [
    "No source patch",
    "dormant legacy DEF stub",
    "No new Windows/API runtime behavior is defined by this stub",
    "not",
    "selected by `SboxDll.vcxproj`",
    "dumpbin",
    "/exports` proof",
]:
    require(spec, term, "spec classification")

for term in [
    "kind: srev-ledger-entry",
    "id: SREV-243",
    "owner: Sandboxie/core/dll/SboxDll.def",
    "docs-only-source-topology-reviewed-dormant-legacy-stub",
    "srev-243-sboxdll-def-legacy-stub.schema.json",
    "check-srev-243.py",
]:
    require(fragment, term, "ledger fragment")
    require(ledger, term, "combined ledger")

print("SREV-243 source gate passed")
