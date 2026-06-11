#!/usr/bin/env python3
import json
from pathlib import Path

from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-216 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-216 failed: stale {label} remains {needle!r}")


def between(text: str, start: str, end: str) -> str:
    a = text.index(start)
    b = text.index(end, a + len(start))
    return text[a:b]


schema = json.loads(
    (ROOT / "docs/plan/srev-216-pdh-status-abi-contract.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-216 failed: schema is not draft-07")
if schema.get("id") != "PDH_STATUS_ABI_CONTRACT":
    raise SystemExit("SREV-216 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/dll/pdh.c":
    raise SystemExit("SREV-216 failed: wrong owner")
if schema.get("declaration") != "Sandboxie/core/dll/dll.h":
    raise SystemExit("SREV-216 failed: wrong declaration")

contracts = "\n".join(schema["contracts"])
for term in [
    "PDH deny hooks",
    "PDH_STATUS",
    "official PDH return contract",
    "resolved export ABI",
    "PDH_ACCESS_DENIED",
    "Hook installation",
]:
    require(contracts, term, "schema contract")

spec = (ROOT / "docs/plan/srev-216-pdh-status-abi-contract.md").read_text()
source = (ROOT / "Sandboxie/core/dll/pdh.c").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-216.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

require(source, "#include <pdh.h>", "pdh header")
require(source, "#include <pdhmsg.h>", "pdh message header")
require(source, "#define PDH_ACCESS_DENIED ((PDH_STATUS)0xC0000BDBL)", "PDH access denied fallback")
for term in [
    "static _FX PDH_STATUS Pdh_PdhConnectMachineW(LPCWSTR lpwsMachine);",
    "static _FX PDH_STATUS Pdh_PdhLookupPerfNameByIndexW(",
    "typedef PDH_STATUS(*P_PdhConnectMachineW)(",
    "typedef PDH_STATUS(*P_PdhLookupPerfNameByIndexW)(",
]:
    require(source, term, "PDH_STATUS ABI")

init = between(
    source,
    "_FX BOOLEAN Pdh_Init(HMODULE module)",
    "//---------------------------------------------------------------------------\n// Pdh_PdhConnectMachineW",
)
for term in [
    'GetProcAddress(module, "PdhConnectMachineW")',
    'GetProcAddress(module, "PdhLookupPerfNameByIndexW")',
    "SBIEDLL_HOOK(Pdh_, PdhConnectMachineW);",
    "SBIEDLL_HOOK(Pdh_, PdhLookupPerfNameByIndexW);",
]:
    require(init, term, "hook install topology")

connect = between(
    source,
    "static _FX PDH_STATUS Pdh_PdhConnectMachineW(LPCWSTR lpwsMachine)",
    "//---------------------------------------------------------------------------\n// Pdh_PdhLookupPerfNameByIndexW",
)
lookup = source[source.index("static _FX PDH_STATUS Pdh_PdhLookupPerfNameByIndexW("):]
require(connect, "return PDH_ACCESS_DENIED;", "connect deny status")
require(lookup, "return PDH_ACCESS_DENIED;", "lookup deny status")

reject(source, "static _FX UINT Pdh_PdhConnectMachineW", "UINT connect hook")
reject(source, "static _FX UINT Pdh_PdhLookupPerfNameByIndexW", "UINT lookup hook")
reject(source, "typedef UINT(*P_PdhConnectMachineW)", "UINT connect typedef")
reject(source, "typedef UINT(*P_PdhLookupPerfNameByIndexW)", "UINT lookup typedef")
reject(source, "return ERROR_ACCESS_DENIED;", "generic PDH deny return")

for term in [
    "kind: srev-ledger-entry",
    "id: SREV-216",
    "owner: Sandboxie/core/dll/pdh.c",
    "declaration: Sandboxie/core/dll/dll.h",
    "spec: docs/plan/srev-216-pdh-status-abi-contract.md",
    "schema: docs/plan/srev-216-pdh-status-abi-contract.schema.json",
    "checker: docs/plan/check-srev-216.py",
    "patched source-level after official PDH status ABI review",
]:
    require(ledger_fragment, term, "ledger fragment")
    require(ledger, term, "combined ledger")

print("SREV-216 source gate passed")
