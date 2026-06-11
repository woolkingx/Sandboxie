#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-205 failed: {label} missing {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-205-mscoree-clr-entry-hook-boundary.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-205 failed: schema is not draft-07")
if schema.get("id") != "MSCOREE_CLR_ENTRY_HOOK_BOUNDARY":
    raise SystemExit("SREV-205 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/dll/mscoree.c":
    raise SystemExit("SREV-205 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "managed executable loader entry",
    "delayed Sandboxie injection edge",
    "Hook installation fails closed",
    "intentionally makes no source mutation",
]:
    require(contracts, term, "schema contract")

src = (ROOT / "Sandboxie/core/dll/mscoree.c").read_text()
hook_macro = (ROOT / "Sandboxie/core/dll/sbiedll.h").read_text()
ldr_init = (ROOT / "Sandboxie/core/dll/ldr_init.c").read_text()
spec = (ROOT / "docs/plan/srev-205-mscoree-clr-entry-hook-boundary.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-205.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "typedef DWORD (__stdcall *P__CorExeMain)();",
    "P__CorExeMain __sys__CorExeMain = NULL;",
    "_FX DWORD MsCorEE__CorExeMain()",
    "Ldr_LoadInjectDlls(g_bHostInject);",
    "bFirstCall = FALSE;",
    "ret = __sys__CorExeMain();",
    "GETPROC(_CorExeMain,);",
    "_CorExeMain = __sys__CorExeMain;",
    "SBIEDLL_HOOK(MsCorEE_,_CorExeMain);",
]:
    require(src, term, "mscoree hook topology")

for term in [
    "SbieDll_Hook(#proc, proc, pfx##proc, module);",
    "if (! __sys_##proc) return FALSE;",
]:
    require(hook_macro, term, "shared hook fail-closed macro")

require(ldr_init, "some .NET programs have a zero entrypoint address", "zero-entrypoint evidence")
require(src, "ReadImageFileExecOptions", "private PEB workaround coordinate")

for term in [
    "kind: srev-ledger-entry",
    "id: SREV-205",
    "owner: Sandboxie/core/dll/mscoree.c",
    "spec: docs/plan/srev-205-mscoree-clr-entry-hook-boundary.md",
    "schema: docs/plan/srev-205-mscoree-clr-entry-hook-boundary.schema.json",
    "checker: docs/plan/check-srev-205.py",
    "classified source-level; no local mutation",
]:
    require(ledger_fragment, term, "ledger fragment")
    require(ledger, term, "combined ledger")

print("SREV-205 source gate passed")
