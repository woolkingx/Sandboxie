#!/usr/bin/env python3
import json
import xml.etree.ElementTree as ET
from pathlib import Path

from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]
NS = {"msb": "http://schemas.microsoft.com/developer/msbuild/2003"}


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-244 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-244 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-244-lowlevel-def-legacy-stub.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-244 failed: schema is not draft-07")
if schema.get("id") != "LOWLEVEL_DEF_LEGACY_STUB_CONTRACT":
    raise SystemExit("SREV-244 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/low/LowLevel.def":
    raise SystemExit("SREV-244 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "legacy DEF stub not the active linker export table",
    "LowLevel.vcxproj lists the file as a None item only",
    "does not set ModuleDefinitionFile",
    "runtime behavior is owned by entry assembly init.c inject.c and SbieDll resource embedding",
    "project cleanup decision",
    "Windows LowLevel.dll build and dumpbin /exports proof",
]:
    require(contracts, term, "schema contract")

spec = (ROOT / "docs/plan/srev-244-lowlevel-def-legacy-stub.md").read_text()
stub = (ROOT / "Sandboxie/core/low/LowLevel.def").read_text()
vcxproj_path = ROOT / "Sandboxie/core/low/LowLevel.vcxproj"
vcxproj = vcxproj_path.read_text()
entry_asm = (ROOT / "Sandboxie/core/low/entry_asm.asm").read_text()
entry_arm = (ROOT / "Sandboxie/core/low/entry_arm.asm").read_text()
init_c = (ROOT / "Sandboxie/core/low/init.c").read_text()
inject_c = (ROOT / "Sandboxie/core/low/inject.c").read_text()
lowlevel_rc = (ROOT / "Sandboxie/core/dll/lowlevel.rc").read_text()
ledger = read_combined_ledger(ROOT)
fragment = (ROOT / "docs/plan/ledger/srev-244.md").read_text()

if stub.strip() != "LIBRARY .TAIL.":
    raise SystemExit("SREV-244 failed: unexpected LowLevel.def body")
reject(stub, "EXPORTS", "active export table in stub")

project = ET.parse(vcxproj_path)
none_items = project.findall(".//msb:None[@Include='LowLevel.def']", NS)
if len(none_items) != 1:
    raise SystemExit("SREV-244 failed: expected one LowLevel.def None item")
if project.findall(".//msb:ModuleDefinitionFile", NS):
    raise SystemExit("SREV-244 failed: LowLevel.vcxproj unexpectedly selects a ModuleDefinitionFile")

for term in [
    "<ConfigurationType>DynamicLibrary</ConfigurationType>",
    "<GenerateManifest>false</GenerateManifest>",
    "<IgnoreAllDefaultLibraries>true</IgnoreAllDefaultLibraries>",
    "<NoEntryPoint>true</NoEntryPoint>",
    "<BaseAddress>0</BaseAddress>",
    '<CustomBuild Include="entry_asm.asm">',
    '<CustomBuild Include="entry_arm.asm">',
    '<None Include="LowLevel.def" />',
    '<ClCompile Include="init.c" />',
    '<ClCompile Include="inject.c" />',
]:
    require(vcxproj, term, "LowLevel project topology")

for term in [
    "_Start:",
    "SbieLowData",
    "EntrypointC",
]:
    require(entry_asm, term, "entry_asm topology")

for term in [
    "EXPORT  SystemServiceARM64",
    "EXPORT  SbieLowData",
    "NtDeviceIoControlFileEC",
]:
    require(entry_arm, term, "entry_arm topology")

for term in [
    "PrepSyscalls",
    "InitInject(data, DetourCode);",
    "SBIELOW_DATA* data = &SbieLowData;",
]:
    require(init_c, term, "init.c topology")

for term in [
    "InitInject",
    "P_Dll_Ordinal1",
    "SbieDllOrdinal1",
]:
    require(inject_c, term, "inject.c topology")

for term in [
    "LOWLEVEL64  RCDATA",
    "LOWLEVEL32  RCDATA",
    "SboxDll.vcxproj compiles this file into SbieDll",
]:
    require(lowlevel_rc, term, "SbieDll lowlevel resource topology")

for term in [
    "SREV-132: Low ARM64 Entry Syscall ABI Contract",
    "SREV-133: Low x64 Entry Nonvolatile Register",
    "SREV-106: Low Inject ARM64EC Syscall Entrypoint",
    "SREV-221: Core Resource Topology",
    "Sandboxie/core/dll/lowlevel.rc",
]:
    require(ledger, term, "existing lowlevel owner coverage")

for term in [
    "No source patch",
    "dormant legacy DEF stub",
    "No new Windows/API runtime behavior is defined by this stub",
    "not a",
    "selected module-definition file",
    "dumpbin",
    "/exports` proof",
]:
    require(spec, term, "spec classification")

for term in [
    "kind: srev-ledger-entry",
    "id: SREV-244",
    "owner: Sandboxie/core/low/LowLevel.def",
    "docs-only-source-topology-reviewed-dormant-legacy-stub",
    "srev-244-lowlevel-def-legacy-stub.schema.json",
    "check-srev-244.py",
]:
    require(fragment, term, "ledger fragment")
    require(ledger, term, "combined ledger")

print("SREV-244 source gate passed")
