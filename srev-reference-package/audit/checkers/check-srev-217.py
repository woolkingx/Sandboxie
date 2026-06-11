#!/usr/bin/env python3
import json
from pathlib import Path

from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-217 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-217 failed: stale {label} remains {needle!r}")


def between(text: str, start: str, end: str) -> str:
    a = text.index(start)
    b = text.index(end, a + len(start))
    return text[a:b]


schema = json.loads(
    (ROOT / "docs/plan/srev-217-evtapi-internal-hook-bool-contract.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-217 failed: schema is not draft-07")
if schema.get("id") != "EVTAPI_INTERNAL_HOOK_BOOL_CONTRACT":
    raise SystemExit("SREV-217 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/dll/event.c":
    raise SystemExit("SREV-217 failed: wrong owner")
if schema.get("declaration") != "Sandboxie/core/dll/dll.h":
    raise SystemExit("SREV-217 failed: wrong declaration")

contracts = "\n".join(schema["contracts"])
for term in [
    "EvtIntAssertConfig hook",
    "internal export has no public Microsoft API page",
    "P_EvtIntAssertConfig typedef",
    "both return BOOL",
    "GetProcAddress returned a non-null export pointer",
    "clear last error",
]:
    require(contracts, term, "schema contract")

spec = (ROOT / "docs/plan/srev-217-evtapi-internal-hook-bool-contract.md").read_text()
source = (ROOT / "Sandboxie/core/dll/event.c").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-217.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "static BOOL Event_EvtIntAssertConfig(",
    "typedef BOOL (*P_EvtIntAssertConfig)(",
    "ALIGNED BOOL Event_EvtIntAssertConfig(",
]:
    require(source, term, "BOOL ABI")

detour = between(
    source,
    "ALIGNED BOOL Event_EvtIntAssertConfig(",
    "//---------------------------------------------------------------------------\n// EvtApi_Init",
)
for term in [
    "SetLastError(0);",
    "return TRUE;",
]:
    require(detour, term, "success policy")

init = source[source.index("ALIGNED BOOLEAN EvtApi_Init(HMODULE module)"):]
for term in [
    'GetProcAddress(module, "EvtIntAssertConfig");',
    "if (! EvtIntAssertConfig)\n        return FALSE;",
    "SBIEDLL_HOOK(Event_,EvtIntAssertConfig);",
    "return TRUE;",
]:
    require(init, term, "init topology")

reject(source, "static BOOLEAN Event_EvtIntAssertConfig", "BOOLEAN forward declaration")
reject(source, "ALIGNED BOOLEAN Event_EvtIntAssertConfig", "BOOLEAN detour definition")
reject(init, 'GetProcAddress(module, "EvtIntAssertConfig");\n\n    SBIEDLL_HOOK', "hook without GetProcAddress gate")

for term in [
    "kind: srev-ledger-entry",
    "id: SREV-217",
    "owner: Sandboxie/core/dll/event.c",
    "declaration: Sandboxie/core/dll/dll.h",
    "spec: docs/plan/srev-217-evtapi-internal-hook-bool-contract.md",
    "schema: docs/plan/srev-217-evtapi-internal-hook-bool-contract.schema.json",
    "checker: docs/plan/check-srev-217.py",
    "patched-source-level-after-official-getprocaddress-and-windows-data-type-review",
]:
    require(ledger_fragment, term, "ledger fragment")
    require(ledger, term, "combined ledger")

print("SREV-217 source gate passed")
