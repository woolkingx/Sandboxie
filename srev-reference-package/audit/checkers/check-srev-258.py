#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-258 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-258 failed: {label} still contains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-258-custom-sysfer-comment-owner.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-258 failed: schema is not draft-07")
if schema.get("id") != "CUSTOM_SYSFER_COMMENT_OWNER":
    raise SystemExit("SREV-258 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "SREV-055 owns",
    "bounded entry-point patch owner",
    "does not change PE validation",
]:
    require(contracts, term, "schema")

source = (ROOT / "Sandboxie/core/dll/custom.c").read_text()
spec = (ROOT / "docs/plan/srev-258-custom-sysfer-comment-owner.md").read_text()
srev_055 = (ROOT / "docs/plan/srev-055-custom-sysfer-entrypoint-patch.md").read_text()
srev_055_check = (ROOT / "docs/plan/check-srev-055.py").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-258.md").read_text()

start = source.index("_FX BOOLEAN Custom_SYSFER_DLL(")
end = source.index("// Handles ActivClient", start)
sysfer = source[start:end]

for term in [
    "SREV-055 owns this",
    "bounded entry-point patch for the SYSFER.DLL load path.",
    "VirtualProtect(entrypoint, sizeof(ULONG), PAGE_EXECUTE_READWRITE, &old_prot)",
    "*(ULONG *)entrypoint = 0x00C301B0;",
    "FlushInstructionCache(GetCurrentProcess(), entrypoint, sizeof(ULONG));",
    "VirtualProtect(entrypoint, sizeof(ULONG), old_prot, &tmp_prot);",
]:
    require(sysfer, term, "Custom_SYSFER_DLL")

reject(sysfer, "workaround to nullify SYSFER.DLL", "Custom_SYSFER_DLL")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")
    require(srev_055, term, "SREV-055 official reference")

for term in [
    "SREV-055 owns this",
    "bounded entry-point patch for the SYSFER.DLL load path.",
    "workaround to nullify SYSFER.DLL",
]:
    require(srev_055_check, term, "SREV-055 checker adjacency")

for term in [
    "source comment points back to this SREV",
    "bounded entry-point patch owner",
]:
    require(srev_055, term, "SREV-055 spec adjacency")

for term in [
    "### SREV-258: Custom SYSFER Comment Owner",
    "CUSTOM_SYSFER_COMMENT_OWNER",
    "srev-258-custom-sysfer-comment-owner.schema.json",
    "Sandboxie/core/dll/custom.c",
    "Custom_SYSFER_DLL",
    "SREV-055",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-258 source gate passed")
