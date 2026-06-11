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
    "SbieDebug|ARM64",
    "SbieRelease|ARM64",
}


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-240 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-240 failed: stale {label} remains {needle!r}")


def condition_config(element: ET.Element) -> str:
    condition = element.attrib.get("Condition", "")
    prefix = "'$(Configuration)|$(Platform)'=='"
    if not condition.startswith(prefix) or not condition.endswith("'"):
        raise SystemExit(f"SREV-240 failed: unexpected MSBuild condition {condition!r}")
    return condition[len(prefix) : -1]


schema = json.loads(
    (ROOT / "docs/plan/srev-240-aulldvrm-legacy-x86-helper.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-240 failed: schema is not draft-07")
if schema.get("id") != "AULLDVRM_LEGACY_X86_HELPER_CONTRACT":
    raise SystemExit("SREV-240 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/drv/aulldvrm.asm":
    raise SystemExit("SREV-240 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "legacy x86 MASM helper for __aulldvrm",
    "non-_WIN64 MASM path",
    "SboxDrv.vcxproj owns whether this helper is built",
    "excludes this helper from all listed driver configurations",
    "No current source call site proves runtime dependence on __aulldvrm",
    "Windows x86 WDK build proof and CRT helper ABI proof",
]:
    require(contracts, term, "schema contract")

spec = (ROOT / "docs/plan/srev-240-aulldvrm-legacy-x86-helper.md").read_text()
asm = (ROOT / "Sandboxie/core/drv/aulldvrm.asm").read_text()
vcxproj_path = ROOT / "Sandboxie/core/drv/SboxDrv.vcxproj"
filters = (ROOT / "Sandboxie/core/drv/SboxDrv.vcxproj.filters").read_text()
ledger = read_combined_ledger(ROOT)
fragment = (ROOT / "docs/plan/ledger/srev-240.md").read_text()

for term in [
    "_aulldvrm support routine is not available on Windows 2000",
    "ulldvrm.obj object file",
    "ifdef _WIN64",
    ".386p",
    ".model flat",
    ".code",
    "__aulldvrm",
    "proc",
    "push    esi",
    "pop     esi",
    "ret     10h",
    "endp",
    "public",
    "endif",
    "end",
]:
    require(asm, term, "legacy x86 helper source")

for forbidden in [
    "EXPORT",
    "armasm64",
    "Sbie_CallZwServiceFunction_asm",
    "Driver_KiServiceInternal",
    "x16",
]:
    reject(asm, forbidden, "ARM64/runtime-owner marker in aulldvrm.asm")

project = ET.parse(vcxproj_path)
custom_builds = project.findall(".//msb:CustomBuild[@Include='aulldvrm.asm']", NS)
if len(custom_builds) != 1:
    raise SystemExit("SREV-240 failed: expected exactly one aulldvrm.asm CustomBuild")
item = custom_builds[0]

commands = {condition_config(cmd): (cmd.text or "") for cmd in item.findall("msb:Command", NS)}
if set(commands) != CONFIGS:
    raise SystemExit(f"SREV-240 failed: command configs mismatch {sorted(commands)}")
for config in ["SbieDebug|Win32", "SbieRelease|Win32"]:
    require(commands[config], "ml -c", f"{config} Win32 ml command")
    require(commands[config], "-Zm", f"{config} Win32 ml command")
    reject(commands[config], "-D_WIN64", f"{config} Win32 command")
for config in ["SbieDebug|x64", "SbieRelease|x64", "SbieDebug|ARM64", "SbieRelease|ARM64"]:
    require(commands[config], "ml64 -c", f"{config} ml64 command")
    require(commands[config], "-D_WIN64", f"{config} ml64 command")

exclusions = {
    condition_config(excluded): (excluded.text or "").strip()
    for excluded in item.findall("msb:ExcludedFromBuild", NS)
}
if set(exclusions) != CONFIGS:
    raise SystemExit(f"SREV-240 failed: exclusion configs mismatch {sorted(exclusions)}")
for config, value in exclusions.items():
    if value != "true":
        raise SystemExit(f"SREV-240 failed: {config} is not excluded from build")

require(filters, '<CustomBuild Include="aulldvrm.asm" />', "filters project tree entry")

source_refs = []
for path in (ROOT / "Sandboxie/core").rglob("*"):
    if not path.is_file():
        continue
    text = path.read_text(errors="ignore")
    if "__aulldvrm" in text and path.name != "aulldvrm.asm":
        source_refs.append(str(path.relative_to(ROOT)))
if source_refs:
    raise SystemExit(f"SREV-240 failed: unexpected __aulldvrm source refs {source_refs}")

for term in [
    "SREV-170: ARM64 Driver Assembly ABI Review",
    "Sandboxie/core/drv/util_arm.asm",
    "Sbie_CallZwServiceFunction_asm",
    "SREV-102: Syscall64 Private Table Scanner Boundary",
    "SREV-132: Low ARM64 Entry Syscall ABI Contract",
]:
    require(ledger, term, "separate architecture SREV coverage")

for term in [
    "No source patch",
    "dormant legacy x86 helper",
    "No new Windows runtime behavior is defined by this file while it is excluded",
    "Future cleanup could remove",
    "the excluded project item",
    "Windows x86 WDK",
    "driver build",
]:
    require(spec, term, "spec classification")

for term in [
    "kind: srev-ledger-entry",
    "id: SREV-240",
    "owner: Sandboxie/core/drv/aulldvrm.asm",
    "docs-only-source-topology-reviewed-dormant-build-surface",
    "srev-240-aulldvrm-legacy-x86-helper.schema.json",
    "check-srev-240.py",
]:
    require(fragment, term, "ledger fragment")
    require(ledger, term, "combined ledger")

print("SREV-240 source gate passed")
