#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-260 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-260 failed: {label} still contains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-260-dllhook-unity-runtime-gate-wording.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-260 failed: schema is not draft-07")
if schema.get("id") != "DLLHOOK_UNITY_RUNTIME_GATE_WORDING":
    raise SystemExit("SREV-260 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "SREV-246 owns",
    "Unity runtime gate",
    "does not change hook bytes",
]:
    require(contracts, term, "schema")

dllhook = (ROOT / "Sandboxie/core/dll/dllhook.c").read_text()
srev_246 = (ROOT / "docs/plan/srev-246-dllhook-unity-nop-padding-boundary.md").read_text()
srev_246_check = (ROOT / "docs/plan/check-srev-246.py").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-260.md").read_text()

for term in [
    "Do not pad the moved instruction tail with NOPs here.",
    "write span to HookTramp's ByteCount needs a Unity runtime gate.",
    "//for(; UsedCount < ByteCount; UsedCount++)",
    "//\tfunc[UsedCount] = 0x90; // nop",
]:
    require(dllhook, term, "dllhook source")

reject(dllhook, "because it has broken Unity games in the past.", "dllhook source")

for term in [
    "Unity runtime gate",
]:
    require(srev_246, term, "SREV-246 spec adjacency")
    require(srev_246_check, term, "SREV-246 checker adjacency")

for term in [
    "### SREV-260: DLL Hook Unity Runtime Gate Wording",
    "DLLHOOK_UNITY_RUNTIME_GATE_WORDING",
    "srev-260-dllhook-unity-runtime-gate-wording.schema.json",
    "Sandboxie/core/dll/dllhook.c",
    "SREV-246",
    "Unity runtime gate",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-260 source gate passed")
