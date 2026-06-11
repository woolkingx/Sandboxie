#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-199 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-199 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-199-sfc-wrp-query-shim-contract.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-199 failed: schema is not draft-07")
if schema.get("id") != "SFC_WRP_QUERY_SHIM_CONTRACT":
    raise SystemExit("SREV-199 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/dll/sfc.c":
    raise SystemExit("SREV-199 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "SfcIsFileProtected uses HANDLE plus LPCWSTR, not LPCWSTR pointer-to-pointer",
    "SfcGetNextProtectedFile reports empty enumeration with ERROR_NO_MORE_FILES",
    "This SREV preserves the local disable-SFC compatibility policy",
]:
    require(contracts, term, "schema contract")

src = (ROOT / "Sandboxie/core/dll/sfc.c").read_text()
ldr = (ROOT / "Sandboxie/core/dll/ldr.c").read_text()
spec = (ROOT / "docs/plan/srev-199-sfc-wrp-query-shim-contract.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-199.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "static BOOL Sfc_SfcIsFileProtected(HANDLE RpcHandle, LPCWSTR ProtFileName);",
    "typedef BOOL (*P_SfcIsFileProtected)(HANDLE RpcHandle, LPCWSTR ProtFileName);",
    "_FX BOOL Sfc_SfcIsFileProtected(HANDLE RpcHandle, LPCWSTR ProtFileName)",
    "// intercept SFC/WRP entry points",
    "SetLastError(ERROR_FILE_NOT_FOUND);",
    "return FALSE;",
    "SetLastError(ERROR_NO_MORE_FILES);",
]:
    require(src, term, "source SFC/WRP shape")

reject(src, "LPCWSTR *FileName", "SfcIsFileProtected pointer-to-pointer shape")
reject(src, "SECUR32 entry points", "stale owner comment")
require(ldr, '{ L"sfc_os.dll",            Sfc_Init,                       0}, // disable SFC', "loader policy comment")

for term in [
    "kind: srev-ledger-entry",
    "id: SREV-199",
    "owner: Sandboxie/core/dll/sfc.c",
    "spec: docs/plan/srev-199-sfc-wrp-query-shim-contract.md",
    "schema: docs/plan/srev-199-sfc-wrp-query-shim-contract.schema.json",
    "checker: docs/plan/check-srev-199.py",
    "patched source-level after official SFC/WRP shape review",
]:
    require(ledger_fragment, term, "ledger fragment")
    require(ledger, term, "combined ledger")

print("SREV-199 source gate passed")
