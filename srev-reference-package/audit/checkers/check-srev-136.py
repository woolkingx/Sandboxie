#!/usr/bin/env python3
import json
import re
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-136 failed: {label} missing {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-136-sboxdll32-def-export-abi-contract.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-136 failed: schema is not draft-07")
if schema.get("id") != "SBOXDLL32_DEF_EXPORT_ABI_CONTRACT":
    raise SystemExit("SREV-136 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "SboxDll32.def is the Win32 linker-owned public export alias table for SbieDll",
    "Win32 project configurations select SboxDll32.def as the ModuleDefinitionFile",
    "x64 ARM64EC and ARM64 project configurations do not select SboxDll32.def",
    "Dll_Ordinal1 remains exported by ordinal 1 with NONAME for injection startup compatibility",
    "Every public Win32 alias in SboxDll32.def maps to an x86 decorated internal symbol",
    "The x86 decorated internal symbol suffix records the byte count for the stdcall parameter list",
    "SboxDll64.def remains a separate minimal 64-bit export table",
    "This SREV records the export ABI shape and does not change source behavior",
]:
    require(contracts, term, "schema")

spec = (ROOT / "docs/plan/srev-136-sboxdll32-def-export-abi-contract.md").read_text()
def32 = (ROOT / "Sandboxie/core/dll/SboxDll32.def").read_text()
def64 = (ROOT / "Sandboxie/core/dll/SboxDll64.def").read_text()
vcxproj = (ROOT / "Sandboxie/core/dll/SboxDll.vcxproj").read_text()
sbieapi_h = (ROOT / "Sandboxie/core/dll/sbieapi.h").read_text()
sbiedll_h = (ROOT / "Sandboxie/core/dll/sbiedll.h").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-136.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "<ModuleDefinitionFile>SboxDll32.def</ModuleDefinitionFile>",
    "<ModuleDefinitionFile>SboxDll64.def</ModuleDefinitionFile>",
    "'$(Configuration)|$(Platform)'=='SbieDebug|Win32'",
    "'$(Configuration)|$(Platform)'=='SbieRelease|Win32'",
    "'$(Configuration)|$(Platform)'=='SbieDebug|x64'",
    "'$(Configuration)|$(Platform)'=='SbieDebug|ARM64EC'",
    "'$(Configuration)|$(Platform)'=='SbieDebug|ARM64'",
]:
    require(vcxproj, term, "SboxDll.vcxproj")

entries = []
for line in def32.splitlines():
    stripped = line.strip()
    if not stripped or stripped.startswith(";") or stripped == "EXPORTS":
        continue
    match = re.fullmatch(
        r"([A-Za-z0-9_]+)(?:=(_[A-Za-z0-9_]+)@(\d+))?(?:\s+@(\d+)\s+NONAME)?",
        stripped,
    )
    if not match:
        raise SystemExit(f"SREV-136 failed: unparsed SboxDll32.def export line {stripped!r}")
    entries.append(match.groups())

if len(entries) != 77:
    raise SystemExit(f"SREV-136 failed: expected 77 SboxDll32 exports, saw {len(entries)}")
aliases = [entry for entry in entries if entry[1]]
if len(aliases) != 76:
    raise SystemExit(f"SREV-136 failed: expected 76 SboxDll32 aliases, saw {len(aliases)}")
if entries[0] != ("Dll_Ordinal1", None, None, "1"):
    raise SystemExit("SREV-136 failed: ordinal 1 NONAME export is not first and stable")
for public, internal, byte_count, ordinal in aliases:
    if ordinal is not None:
        raise SystemExit(f"SREV-136 failed: alias {public} unexpectedly has ordinal {ordinal}")
    if not internal.endswith(public):
        raise SystemExit(f"SREV-136 failed: alias {public} maps to unexpected internal {internal}")
    if int(byte_count) % 4 != 0:
        raise SystemExit(f"SREV-136 failed: alias {public} byte count is not pointer-sized {byte_count}")

for term in [
    "SbieApi_CheckInternetAccess=_SbieApi_CheckInternetAccess@12",
    "SbieApi_QueryBoxPath=_SbieApi_QueryBoxPath@28",
    "SbieDll_RunSandboxed=_SbieDll_RunSandboxed@24",
    "SbieDll_QueueGetReq=_SbieDll_QueueGetReq@24",
    "SbieDll_ComCreateProxy=_SbieDll_ComCreateProxy@16",
    "SbieDll_TranslateNtToDosPath=_SbieDll_TranslateNtToDosPath@4",
]:
    require(def32, term, "SboxDll32.def selected decorated exports")

if def64.strip() != "EXPORTS\n\n;;;\n;;; Ordinal 1\n;;;\n\nDll_Ordinal1 @1 NONAME":
    raise SystemExit("SREV-136 failed: SboxDll64.def is no longer the minimal ordinal-1 export table")

for text, label in [(sbieapi_h, "sbieapi.h"), (sbiedll_h, "sbiedll.h")]:
    require(text, 'extern "C" {', label)
    require(text, "__declspec(dllexport)", label)

for term in [
    "LONG SbieApi_CheckInternetAccess(",
    "LONG SbieApi_QueryBoxPath(",
    "LONG SbieApi_GetVersion(",
]:
    require(sbieapi_h, term, "sbieapi.h public prototypes")
for term in [
    "BOOL SbieDll_RunSandboxed(",
    "ULONG SbieDll_QueueGetReq(",
    "HRESULT SbieDll_ComCreateProxy(",
    "BOOLEAN SbieDll_TranslateNtToDosPath(WCHAR *path);",
]:
    require(sbiedll_h, term, "sbiedll.h public prototypes")

for term in [
    "kind: srev-ledger-entry",
    "id: SREV-136",
    "owner: Sandboxie/core/dll/SboxDll32.def",
    "checker: docs/plan/check-srev-136.py",
]:
    require(ledger_fragment, term, "ledger fragment header")

for term in [
    "### SREV-136: SboxDll32 DEF Export ABI Contract",
    "SBOXDLL32_DEF_EXPORT_ABI_CONTRACT",
    "srev-136-sboxdll32-def-export-abi-contract.schema.json",
    "Sandboxie/core/dll/SboxDll32.def",
    "Sandboxie/core/dll/SboxDll64.def",
    "Sandboxie/core/dll/SboxDll.vcxproj",
    "Sandboxie/core/dll/sbieapi.h",
    "Sandboxie/core/dll/sbiedll.h",
    "Dll_Ordinal1 @1 NONAME",
    "ModuleDefinitionFile",
    "dumpbin /exports",
]:
    require(ledger, term, "ledger")

print("SREV-136 schema/source gate passed")
