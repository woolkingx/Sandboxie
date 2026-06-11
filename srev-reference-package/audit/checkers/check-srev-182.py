#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-182 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-182 failed: {label} still contains {needle!r}")


def assert_before(text: str, label: str, earlier: str, later: str) -> None:
    e = text.find(earlier)
    l = text.find(later)
    if e < 0 or l < 0 or e > l:
        raise SystemExit(f"SREV-182 failed: {label}")


schema = json.loads((ROOT / "docs/plan/srev-182-driver-hook-header-guard-boundary.schema.json").read_text())
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-182 failed: schema is not draft-07")
if schema.get("id") != "DRIVER_HOOK_HEADER_GUARD_BOUNDARY":
    raise SystemExit("SREV-182 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "drv/hook.h owns driver-side hook declarations",
    "dll/hook.h owns shared trampoline",
    "driver-owned include guard independent from dll/hook.h",
    "must not rely on dll/hook.h to define the driver guard",
    "including dll/hook.h before drv/hook.h must not suppress driver-only prototypes",
    "Hook_GetService Hook_GetNtServiceInternal Hook_GetZwServiceInternal and Hook_Api_Tramp",
]:
    require(contracts, term, "schema contracts")

drv_hook = (ROOT / "Sandboxie/core/drv/hook.h").read_text()
dll_hook = (ROOT / "Sandboxie/core/dll/hook.h").read_text()
hook_c = (ROOT / "Sandboxie/core/drv/hook.c").read_text()
hook32 = (ROOT / "Sandboxie/core/drv/hook_32.c").read_text()
hook64 = (ROOT / "Sandboxie/core/drv/hook_64.c").read_text()
spec = (ROOT / "docs/plan/srev-182-driver-hook-header-guard-boundary.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-182.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "#ifndef _MY_DRV_HOOK_H",
    "#define _MY_DRV_HOOK_H",
    "#include \"../dll/hook.h\"",
    "BOOLEAN Hook_GetService(",
    "void *Hook_GetNtServiceInternal(ULONG ServiceIndex, ULONG ParamCount);",
    "void *Hook_GetZwServiceInternal(ULONG ServiceIndex);",
    "NTSTATUS Hook_Api_Tramp(PROCESS *proc, ULONG64 *parms);",
    "#endif // _MY_DRV_HOOK_H",
]:
    require(drv_hook, term, "driver hook header")

for term in [
    "#ifndef _MY_HOOK_H",
    "#define _MY_HOOK_H",
    "typedef struct _HOOK_TRAMP",
    "void *Hook_BuildTramp(",
]:
    require(dll_hook, term, "DLL hook header")

reject(drv_hook, "//#define _MY_HOOK_H", "stale shared guard comment")
reject(drv_hook, "#ifndef _MY_HOOK_H", "driver header using shared guard")
reject(drv_hook, "#endif // _MY_HOOK_H", "driver header closing shared guard")
assert_before(drv_hook, "driver guard before DLL include", "#define _MY_DRV_HOOK_H", "#include \"../dll/hook.h\"")
assert_before(drv_hook, "DLL include before driver prototypes", "#include \"../dll/hook.h\"", "BOOLEAN Hook_GetService(")

for term in [
    "#define HOOK_WITH_PRIVATE_PARTS\n#include \"hook.h\"",
    "svc_addr = Hook_GetNtServiceInternal(svc_num, ParamCount);",
    "svc_addr = Hook_GetZwServiceInternal(svc_num);",
    "_FX NTSTATUS Hook_Api_Tramp(PROCESS *proc, ULONG64 *parms)",
]:
    require(hook_c, term, "driver hook.c implementation")

for term in [
    "_FX void *Hook_GetNtServiceInternal(ULONG ServiceIndex, ULONG ParamCount)",
    "_FX void *Hook_GetZwServiceInternal(ULONG ServiceIndex)",
]:
    require(hook32, term, "hook_32 implementation")
    require(hook64, term, "hook_64 implementation")

for term in [
    "include guard",
    "prevent multiple inclusions",
    "_MY_DRV_HOOK_H",
    "_MY_HOOK_H",
    "No hook implementation",
]:
    require(spec, term, "spec shape")

for term in [
    "kind: srev-ledger-entry",
    "id: SREV-182",
    "owner: Sandboxie/core/drv/hook.h",
    "checker: docs/plan/check-srev-182.py",
]:
    require(ledger_fragment, term, "ledger fragment header")

for term in [
    "### SREV-182: Driver Hook Header Guard Boundary",
    "DRIVER_HOOK_HEADER_GUARD_BOUNDARY",
    "Sandboxie/core/drv/hook.h",
    "Sandboxie/core/dll/hook.h",
    "_MY_DRV_HOOK_H",
    "_MY_HOOK_H",
]:
    require(ledger, term, "ledger")

print("SREV-182 schema/source gate passed")
