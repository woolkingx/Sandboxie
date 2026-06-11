#!/usr/bin/env python3
import json
from pathlib import Path

from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-230 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-230 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-230-service-pch-boundary-contract.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-230 failed: schema is not draft-07")
if schema.get("id") != "SERVICE_PCH_BOUNDARY_CONTRACT":
    raise SystemExit("SREV-230 failed: wrong schema id")

owners = set(schema["owners"])
for owner in [
    "Sandboxie/core/svc/stdafx.h",
    "Sandboxie/core/svc/stdafx.cpp",
]:
    if owner not in owners:
        raise SystemExit(f"SREV-230 failed: owner missing {owner}")

contracts = "\n".join(schema["contracts"])
for term in [
    "service compile environment",
    "PCH creation",
    "SboxSvc.vcxproj owns the build topology",
    "_HAS_EXCEPTIONS 0 is a compile contract",
    "WIN32_NO_STATUS and the local NTSTATUS typedef",
    "Runtime defects belong to the concrete service owner",
]:
    require(contracts, term, "schema contract")

spec = (ROOT / "docs/plan/srev-230-service-pch-boundary-contract.md").read_text()
stdafx_h = (ROOT / "Sandboxie/core/svc/stdafx.h").read_text()
stdafx_cpp = (ROOT / "Sandboxie/core/svc/stdafx.cpp").read_text()
vcxproj = (ROOT / "Sandboxie/core/svc/SboxSvc.vcxproj").read_text()
ledger = read_combined_ledger(ROOT)
fragment = (ROOT / "docs/plan/ledger/srev-230.md").read_text()

for term in [
    "#pragma once",
    "#define _HAS_EXCEPTIONS 0",
    "#include <ntstatus.h>",
    "#define WIN32_NO_STATUS",
    "typedef long NTSTATUS;",
    "#define VC_EXTRALEAN",
    "#include <windows.h>",
    '#include "common/defines.h"',
    '#include "core/dll/sbiedll.h"',
]:
    require(stdafx_h, term, "stdafx.h compile environment")

if stdafx_cpp.strip().splitlines()[-1] != '#include "stdafx.h"':
    raise SystemExit("SREV-230 failed: stdafx.cpp does not end as PCH creator include")
reject(stdafx_cpp, '#include <windows.h>', "extra stdafx.cpp include")
reject(stdafx_cpp, "SbieApi_Call", "runtime logic in stdafx.cpp")

for term in [
    '<ClCompile Include="stdafx.cpp">',
    '<ClInclude Include="stdafx.h" />',
    "<PrecompiledHeader>Use</PrecompiledHeader>",
    ">Create</PrecompiledHeader>",
]:
    require(vcxproj, term, "SboxSvc PCH topology")

for term in [
    "No source patch",
    "local MSVC/service compile-topology classification",
    "absence of runtime owner claims",
    "Windows `SboxSvc` build",
]:
    require(spec, term, "spec classification")

for forbidden in [
    "runtime IPC owner",
    "COM behavior owner",
    "RPC behavior owner",
    "driver policy owner",
]:
    reject(spec.lower(), forbidden, "wrong ownership claim")

for term in [
    "kind: srev-ledger-entry",
    "id: SREV-230",
    "owner: Sandboxie/core/svc/stdafx.h",
    "Sandboxie/core/svc/stdafx.cpp",
    "docs-only-source-topology-reviewed",
    "srev-230-service-pch-boundary-contract.schema.json",
    "check-srev-230.py",
]:
    require(fragment, term, "ledger fragment")
    require(ledger, term, "combined ledger")

print("SREV-230 source gate passed")
