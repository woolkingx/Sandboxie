#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-248 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-248 failed: {label} still contains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-248-crypt-norton-export-lookup-boundary.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-248 failed: schema is not draft-07")
if schema.get("id") != "CRYPT_NORTON_EXPORT_LOOKUP_BOUNDARY":
    raise SystemExit("SREV-248 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "GetProcAddress returns NULL",
    "SBIEDLL_HOOK treats a null hook result as module-init failure",
    "install the complete Crypt32 hook surface or skip it",
    "not a DPAPI wire-schema fix",
    "missing CryptProtectData",
    "does not change Crypt32 hook behavior",
]:
    require(contracts, term, "schema")

crypt = (ROOT / "Sandboxie/core/dll/crypt.c").read_text()
sbiedll_h = (ROOT / "Sandboxie/core/dll/sbiedll.h").read_text()
spec = (ROOT / "docs/plan/srev-248-crypt-norton-export-lookup-boundary.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-248.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "CryptProtectData = GetProcAddress(module, \"CryptProtectData\");",
    "CryptUnprotectData = GetProcAddress(module, \"CryptUnprotectData\");",
    "GetProcAddress(module, \"CertGetCertificateChain\");",
    "Norton 360 toolbar can make the CryptProtectData export lookup fail on",
    "skip Crypt32 hooks for that process instead of failing Crypt_Init.",
    "if ((! CryptProtectData) && (Dll_OsBuild >= 8400)",
    "&& GetModuleHandle(L\"UMEngx86.dll\"))",
    "return TRUE;",
    "SBIEDLL_HOOK(Crypt_,CryptProtectData);",
    "SBIEDLL_HOOK(Crypt_,CryptUnprotectData);",
    "SBIEDLL_HOOK(Crypt_,CertGetCertificateChain);",
]:
    require(crypt, term, "crypt source")

reject(crypt, "$Workaround$ - 3rd party fix", "stale workaround label")

for term in [
    "#define SBIEDLL_HOOK(pfx,proc)",
    "SbieDll_Hook(#proc, proc, pfx##proc, module);",
    "if (! __sys_##proc) return FALSE;",
]:
    require(sbiedll_h, term, "hook macro")

for term in [
    "SREV-029 already owns the DPAPI broker wire schema",
    "GetProcAddress(CryptProtectData) fails",
    "do not install partial Crypt32 hook surface",
    "Comment-only source clarification",
]:
    require(spec, term, "spec local contract")

for term in [
    "### SREV-248: Crypt Norton Export Lookup Boundary",
    "CRYPT_NORTON_EXPORT_LOOKUP_BOUNDARY",
    "srev-248-crypt-norton-export-lookup-boundary.schema.json",
    "Sandboxie/core/dll/crypt.c",
    "GetProcAddress",
    "SBIEDLL_HOOK",
    "UMEngx86.dll",
    "SREV-029",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-248 source gate passed")
