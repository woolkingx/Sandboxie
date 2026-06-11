#!/usr/bin/env python3
import json
from pathlib import Path

from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-221 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-221 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-221-core-resource-topology.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-221 failed: schema is not draft-07")
if schema.get("id") != "CORE_RESOURCE_TOPOLOGY":
    raise SystemExit("SREV-221 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/dll/lowlevel.rc":
    raise SystemExit("SREV-221 failed: wrong owner")
if schema.get("consumer") != "Sandboxie/core/dll/lowlevel_inject.c":
    raise SystemExit("SREV-221 failed: wrong consumer")

contracts = "\n".join(schema["contracts"])
for term in [
    "compiled into SbieDll",
    "LOWLEVEL32 and LOWLEVEL64 RCDATA",
    "Dll_Instance",
    "VERSIONINFO metadata",
    "resource2.h is not compiled",
    "resource consumer or project build topology",
]:
    require(contracts, term, "schema contract")

spec = (ROOT / "docs/plan/srev-221-core-resource-topology.md").read_text()
lowlevel_rc = (ROOT / "Sandboxie/core/dll/lowlevel.rc").read_text()
inject = (ROOT / "Sandboxie/core/dll/lowlevel_inject.c").read_text()
dll_proj = (ROOT / "Sandboxie/core/dll/SboxDll.vcxproj").read_text()
svc_proj = (ROOT / "Sandboxie/core/svc/SboxSvc.vcxproj").read_text()
dll_res = (ROOT / "Sandboxie/core/dll/resource.rc").read_text()
drv_res = (ROOT / "Sandboxie/core/drv/resource.rc").read_text()
svc_res = (ROOT / "Sandboxie/core/svc/resource.rc").read_text()
resource2 = (ROOT / "Sandboxie/core/svc/resource2.h").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-221.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    '<ResourceCompile Include="lowlevel.rc" />',
    '<ResourceCompile Include="resource.rc" />',
]:
    require(dll_proj, term, "SboxDll project")

reject(svc_proj, '<ResourceCompile Include="resource2.h"', "current service resource2 compile")

for term in [
    "Low Level DLL embedded into SbieDll as binary resources",
    "SboxDll.vcxproj compiles this file into SbieDll",
    "lowlevel_inject.c reads",
    "LOWLEVEL64  RCDATA",
    "LOWLEVEL32  RCDATA",
    "../low/obj/ARM64/LowLevel.dll",
    "../low/obj/amd64/LowLevel.dll",
    "../low/obj/i386/LowLevel.dll",
]:
    require(lowlevel_rc, term, "lowlevel.rc topology")
reject(lowlevel_rc, "SbieSvc", "lowlevel.rc wrong module owner")

for term in [
    "embedded in SbieDll, see lowlevel.rc",
    "FindResource(Dll_Instance, arch_64bit ? L\"LOWLEVEL64\" : L\"LOWLEVEL32\", RT_RCDATA)",
    "SizeofResource(Dll_Instance, hrsrc)",
    "LoadResource(Dll_Instance, hrsrc)",
    "LockResource(hglob)",
]:
    require(inject, term, "lowlevel resource consumer")
reject(inject, "embedded within the SbieSvc executable", "lowlevel_inject wrong module owner")

for source, label, filename in [
    (dll_res, "DLL resource", "SbieDll.dll"),
    (drv_res, "driver resource", "SbieDrv.sys"),
    (svc_res, "service resource", "SbieSvc.exe"),
]:
    for term in [
        "VS_VERSION_INFO VERSIONINFO",
        "FILEVERSION MY_VERSION_BINARY",
        "PRODUCTVERSION MY_VERSION_BINARY",
        'VALUE "FileDescription"',
        f'OPTIONAL_VALUE("OriginalFilename", "{filename}\\0")',
    ]:
        require(source, term, label)

for term in [
    "LOWLEVEL  RCDATA",
    "../low/obj/amd64/LowLevel.dll",
    "../low/obj/i386/LowLevel.dll",
]:
    require(resource2, term, "legacy resource2.h")

for term in [
    "kind: srev-ledger-entry",
    "id: SREV-221",
    "owner: Sandboxie/core/dll/lowlevel.rc",
    "Sandboxie/core/svc/resource2.h",
    "consumer: Sandboxie/core/dll/lowlevel_inject.c",
    "spec: docs/plan/srev-221-core-resource-topology.md",
    "schema: docs/plan/srev-221-core-resource-topology.schema.json",
    "checker: docs/plan/check-srev-221.py",
    "patched-comment-topology-after-official-resource-and-versioninfo-review",
]:
    require(ledger_fragment, term, "ledger fragment")
    require(ledger, term, "combined ledger")

print("SREV-221 source gate passed")
