#!/usr/bin/env python3
import json
from pathlib import Path

from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-219 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-219 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-219-core-include-aggregator-contract.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-219 failed: schema is not draft-07")
if schema.get("id") != "CORE_INCLUDE_AGGREGATOR_CONTRACT":
    raise SystemExit("SREV-219 failed: wrong schema id")

owners = set(schema["owners"])
for owner in [
    "Sandboxie/core/drv/includes.c",
    "Sandboxie/core/dll/includes.c",
    "Sandboxie/core/svc/includes.cpp",
]:
    if owner not in owners:
        raise SystemExit(f"SREV-219 failed: owner missing {owner}")

contracts = "\n".join(schema["contracts"])
for term in [
    "compile translation unit",
    "KERNEL_MODE",
    "DLL headers",
    "extern C linkage",
    "target-local macros",
    "included common module",
    "target-specific macro, linkage, and included-module topology",
]:
    require(contracts, term, "schema contract")

spec = (ROOT / "docs/plan/srev-219-core-include-aggregator-contract.md").read_text()
drv = (ROOT / "Sandboxie/core/drv/includes.c").read_text()
dll = (ROOT / "Sandboxie/core/dll/includes.c").read_text()
svc = (ROOT / "Sandboxie/core/svc/includes.cpp").read_text()
drv_proj = (ROOT / "Sandboxie/core/drv/SboxDrv.vcxproj").read_text()
dll_proj = (ROOT / "Sandboxie/core/dll/SboxDll.vcxproj").read_text()
svc_proj = (ROOT / "Sandboxie/core/svc/SboxSvc.vcxproj").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-219.md").read_text()

for term in [
    '<ClCompile Include="includes.c" />',
]:
    require(drv_proj, term, "driver project ownership")
    require(dll_proj, term, "DLL project ownership")
require(svc_proj, '<ClCompile Include="includes.cpp" />', "service project ownership")

for term in [
    '#include "my_winnt.h"',
    "#define KERNEL_MODE",
    "extern const ULONG tzuk;",
    "#define POOL_TAG tzuk",
    '#include "common/list.c"',
    '#include "common/pool.c"',
    '#include "common/stream.c"',
    '#include "common/pattern.c"',
    '#include "common/map.c"',
    '#include "common/netfw.c"',
    '#include "common/str_util.c"',
]:
    require(drv, term, "driver include topology")

for term in [
    '#include "dll.h"',
    "#include <windows.h>",
    '#include "common/win32_ntddk.h"',
    "extern const ULONG tzuk;",
    "#define POOL_TAG tzuk",
    '#include "common/list.c"',
    '#include "common/pool.c"',
    '#include "common/map.c"',
    '#include "common/stream.c"',
    '#include "common/netfw.c"',
    '#include "common/str_util.c"',
]:
    require(dll, term, "DLL include topology")

for term in [
    '#include "stdafx.h"',
    '#include "common/win32_ntddk.h"',
    'extern "C" const ULONG tzuk;',
    "#define POOL_TAG tzuk",
    'extern "C" {',
    '#include "common/list.c"',
    '#include "common/pool.c"',
    '#include "common/map.c"',
    '#include "common/crc.c"',
    '#include "common/rc4.c"',
    "#define PATTERN XPATTERN",
    '#include "common/pattern.c"',
    '#include "common/stream.c"',
    '#include "common/str_util.c"',
    '#include "common/verify.c"',
]:
    require(svc, term, "service include topology")

for forbidden in [
    "runtime API owner",
    "IPC owner",
    "service handler owner",
    "driver policy owner",
]:
    reject(spec.lower(), forbidden, "wrong ownership claim")

for term in [
    "kind: srev-ledger-entry",
    "id: SREV-219",
    "owner: Sandboxie/core/drv/includes.c",
    "Sandboxie/core/dll/includes.c",
    "Sandboxie/core/svc/includes.cpp",
    "spec: docs/plan/srev-219-core-include-aggregator-contract.md",
    "schema: docs/plan/srev-219-core-include-aggregator-contract.schema.json",
    "checker: docs/plan/check-srev-219.py",
    "docs-only-source-topology-reviewed",
]:
    require(ledger_fragment, term, "ledger fragment")
    require(ledger, term, "combined ledger")

print("SREV-219 source gate passed")
