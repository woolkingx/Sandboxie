#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-188 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-188 failed: {label} still contains {needle!r}")


def function_slice(text: str, start: str, end: str) -> str:
    s = text.index(start)
    e = text.index(end, s)
    return text[s:e]


schema = json.loads(
    (ROOT / "docs/plan/srev-188-conf-expand-early-exit-pool-lifetime.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-188 failed: schema is not draft-07")
if schema.get("id") != "CONF_EXPAND_EARLY_EXIT_POOL_LIFETIME":
    raise SystemExit("SREV-188 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/drv/conf_expand.c":
    raise SystemExit("SREV-188 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "Conf_Expand_2 owns",
    "ExAllocatePoolWithTag",
    "ExFreePoolWithTag",
    "Mem_FreeString",
    "too-long gate",
    "recursion gate",
    "does not change expansion variable lookup",
    "runtime proof is required",
]:
    require(contracts, term, "schema contracts")

conf_expand = (ROOT / "Sandboxie/core/drv/conf_expand.c").read_text()
spec = (ROOT / "docs/plan/srev-188-conf-expand-early-exit-pool-lifetime.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-188.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

body = function_slice(
    conf_expand,
    "_FX WCHAR *Conf_Expand_2(CONF_EXPAND_ARGS *args, const WCHAR *model_value)",
    "//---------------------------------------------------------------------------\n// Conf_Expand",
)

for term in [
    "Conf_Expand_Buffer = ExAllocatePoolWithTag(PagedPool, PAGE_SIZE, tzuk);",
    "if (! Conf_Expand_Buffer)",
    "if (wcslen(new_value) > 1024)",
    "if (new_value != model_value)",
    "Mem_FreeString(new_value);",
    "new_value = NULL;",
    "break;",
    "if (retries > 10)",
    "ExFreePoolWithTag(Conf_Expand_Buffer, tzuk);",
    "return new_value;",
]:
    require(body, term, "Conf_Expand_2 lifetime source")

reject(body, "L\"(TooLong)\");\n            return NULL;", "too-long early return")
reject(body, "L\"(Recursion)\");\n            return NULL;", "recursion early return")

for term in [
    "ExAllocatePoolWithTag",
    "ExFreePoolWithTag",
    "TooLong",
    "Recursion",
    "Conf_Expand_Buffer",
    "No expansion lookup order",
]:
    require(spec, term, "spec shape")

for term in [
    "kind: srev-ledger-entry",
    "id: SREV-188",
    "owner: Sandboxie/core/drv/conf_expand.c",
    "spec: docs/plan/srev-188-conf-expand-early-exit-pool-lifetime.md",
    "schema: docs/plan/srev-188-conf-expand-early-exit-pool-lifetime.schema.json",
    "checker: docs/plan/check-srev-188.py",
]:
    require(ledger_fragment, term, "ledger fragment header")

for term in [
    "### SREV-188: Conf Expand Early Exit Pool Lifetime",
    "CONF_EXPAND_EARLY_EXIT_POOL_LIFETIME",
    "Sandboxie/core/drv/conf_expand.c",
    "Conf_Expand_2",
    "Conf_Expand_Buffer",
]:
    require(ledger, term, "combined ledger")

print("SREV-188 schema/source gate passed")
