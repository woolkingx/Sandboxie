#!/usr/bin/env python3
import json
import xml.etree.ElementTree as ET
from pathlib import Path

from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]
NS = {"msb": "http://schemas.microsoft.com/developer/msbuild/2003"}
CONFIGS = {
    "SbieDebug|Win32",
    "SbieRelease|Win32",
    "SbieDebug|x64",
    "SbieRelease|x64",
    "SbieDebug|ARM64EC",
    "SbieRelease|ARM64EC",
    "SbieDebug|ARM64",
    "SbieRelease|ARM64",
}


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-242 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-242 failed: stale {label} remains {needle!r}")


def condition_config(element: ET.Element) -> str:
    condition = element.attrib.get("Condition", "")
    prefix = "'$(Configuration)|$(Platform)'=='"
    if not condition.startswith(prefix) or not condition.endswith("'"):
        raise SystemExit(f"SREV-242 failed: unexpected MSBuild condition {condition!r}")
    return condition[len(prefix) : -1]


schema = json.loads(
    (ROOT / "docs/plan/srev-242-util-asm-dispatcher-topology.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-242 failed: schema is not draft-07")
if schema.get("id") != "DLL_UTIL_ASM_DISPATCHER_TOPOLOGY_CONTRACT":
    raise SystemExit("SREV-242 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/dll/util_asm.asm":
    raise SystemExit("SREV-242 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "DLL utility assembly dispatcher for MASM include selection",
    "util_32.asm owns the 32-bit implementation body",
    "util_64.asm owns the x64 and ARM64EC MASM body",
    "Native ARM64 runtime assembly is not owned by this dispatcher",
    "SboxDll.vcxproj owns the active platform build selection",
    "included source bodies not direct project build items",
    "Behavior or ABI changes must target the included implementation owner",
]:
    require(contracts, term, "schema contract")

spec = (ROOT / "docs/plan/srev-242-util-asm-dispatcher-topology.md").read_text()
dispatcher = (ROOT / "Sandboxie/core/dll/util_asm.asm").read_text()
util32 = (ROOT / "Sandboxie/core/dll/util_32.asm").read_text()
util64 = (ROOT / "Sandboxie/core/dll/util_64.asm").read_text()
utilarm = (ROOT / "Sandboxie/core/dll/util_arm.asm").read_text()
utilec = (ROOT / "Sandboxie/core/dll/util_EC.asm").read_text()
vcxproj_path = ROOT / "Sandboxie/core/dll/SboxDll.vcxproj"
filters = (ROOT / "Sandboxie/core/dll/SboxDll.vcxproj.filters").read_text()
ledger = read_combined_ledger(ROOT)
fragment = (ROOT / "docs/plan/ledger/srev-242.md").read_text()

for term in [
    "Assembler Utilities",
    "ifndef _WIN64",
    ".386p",
    ".model flat",
    ".code",
    "ifdef _WIN64",
    "include util_64.asm",
    "include util_32.asm",
    "endif",
    "end",
]:
    require(dispatcher, term, "dispatcher source")

for forbidden in [
    "PROC",
    "PUBLIC",
    "EXPORT",
    "ApiInstrumentationAsm",
    "InstrumentationCallbackAsm",
    "RpcRt_Ndr",
    "ProtectCall",
]:
    reject(dispatcher, forbidden, "runtime helper body in dispatcher")

project = ET.parse(vcxproj_path)
custom_builds = project.findall(".//msb:CustomBuild[@Include='util_asm.asm']", NS)
if len(custom_builds) != 1:
    raise SystemExit("SREV-242 failed: expected exactly one util_asm.asm CustomBuild")
item = custom_builds[0]

commands = {condition_config(cmd): (cmd.text or "") for cmd in item.findall("msb:Command", NS)}
if set(commands) != CONFIGS:
    raise SystemExit(f"SREV-242 failed: command configs mismatch {sorted(commands)}")
for config in ["SbieDebug|Win32", "SbieRelease|Win32"]:
    require(commands[config], "ml -c", f"{config} Win32 ml command")
    reject(commands[config], "-D_WIN64", f"{config} Win32 command")
for config in ["SbieDebug|x64", "SbieRelease|x64"]:
    require(commands[config], "ml64 -c", f"{config} x64 ml64 command")
    require(commands[config], "-D_WIN64", f"{config} x64 ml64 command")
    reject(commands[config], "-D_M_ARM64EC", f"{config} x64 command")
for config in ["SbieDebug|ARM64EC", "SbieRelease|ARM64EC"]:
    require(commands[config], "ml64 -c", f"{config} ARM64EC ml64 command")
    require(commands[config], "-D_WIN64", f"{config} ARM64EC command")
    require(commands[config], "-D_M_ARM64EC", f"{config} ARM64EC command")
for config in ["SbieDebug|ARM64", "SbieRelease|ARM64"]:
    require(commands[config], "ml64 -c", f"{config} ARM64 ml64 command")
    require(commands[config], "-D_WIN64", f"{config} ARM64 command")

exclusions = {
    condition_config(excluded): (excluded.text or "").strip()
    for excluded in item.findall("msb:ExcludedFromBuild", NS)
}
expected_exclusions = {
    "SbieRelease|ARM64EC": "false",
    "SbieDebug|ARM64EC": "false",
    "SbieRelease|ARM64": "true",
    "SbieDebug|ARM64": "true",
}
if exclusions != expected_exclusions:
    raise SystemExit(f"SREV-242 failed: util_asm exclusions mismatch {exclusions}")

for term in [
    '<CustomBuild Include="util_asm.asm">',
    "<Filter>hook</Filter>",
]:
    require(filters, term, "filters dispatcher entry")

for term in [
    '<None Include="util_32.asm">',
    '<None Include="util_64.asm">',
    '<CustomBuild Include="util_arm.asm">',
    '<CustomBuild Include="util_EC.asm">',
]:
    require(vcxproj_path.read_text(), term, "related assembly project item")

for term in [
    "Assembler Utilities -- 32-bit",
    "_ProtectCall2@12",
    "RpcRt_NdrAsyncClientCall",
    "ApiInstrumentationAsm@0",
    "PUBLIC C ApiInstrumentationAsm@0",
]:
    require(util32, term, "util_32 included implementation")

for term in [
    "Assembler Utilities -- 64-bit",
    "ProtectCall2",
    "ifndef _M_ARM64EC",
    "RpcRt_Ndr64AsyncClientCall",
    "ApiInstrumentationAsm proc FRAME",
]:
    require(util64, term, "util_64 included implementation")

for term in [
    "EXPORT ApiInstrumentationAsm",
    "ApiInstrumentationAsm PROC",
]:
    require(utilarm, term, "native ARM64 owner")
    require(utilec, term, "ARM64EC owner")

for term in [
    "SREV-095: ARM64 API Instrumentation ABI",
    "Sandboxie/core/dll/util_arm.asm",
    "SREV-177: ARM64EC API Instrumentation Argument Preservation",
    "Sandboxie/core/dll/util_EC.asm",
    "Sandboxie/core/dll/util_64.asm",
    "SREV-164: x64 Syscall Count Width",
    "Sandboxie/core/drv/util_asm.asm",
]:
    require(ledger, term, "existing architecture owner coverage")

for term in [
    "No source patch",
    "DLL MASM include",
    "dispatcher and closes it as docs-only coverage",
    "No new Windows/API runtime behavior is defined by this dispatcher",
    "build-selection node",
    "concrete owner SREV Windows gates",
]:
    require(spec, term, "spec classification")

for term in [
    "kind: srev-ledger-entry",
    "id: SREV-242",
    "owner: Sandboxie/core/dll/util_asm.asm",
    "docs-only-source-topology-reviewed",
    "srev-242-util-asm-dispatcher-topology.schema.json",
    "check-srev-242.py",
]:
    require(fragment, term, "ledger fragment")
    require(ledger, term, "combined ledger")

print("SREV-242 source gate passed")
