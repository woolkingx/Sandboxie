#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-259 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-259 failed: {label} still contains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-259-custom-acscmonitor-loader-reference.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-259 failed: schema is not draft-07")
if schema.get("id") != "CUSTOM_ACSCMONITOR_LOADER_REFERENCE":
    raise SystemExit("SREV-259 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "extra loader reference",
    "LoadLibraryW FreeLibrary per-process module reference-count model",
    "CreateThread is only the deferral execution edge",
    "does not change the loaded DLL name",
]:
    require(contracts, term, "schema")

source = (ROOT / "Sandboxie/core/dll/custom.c").read_text()
spec = (ROOT / "docs/plan/srev-259-custom-acscmonitor-loader-reference.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-259.md").read_text()

start = source.index("// Handles ActivClient's acscmonitor.dll")
acsc = source[start:]

for term in [
    "Handles ActivClient's acscmonitor.dll loader reference lifetime.",
    "Acscmonitor is a plugin to Firefox which creates a thread on initialize.",
    "Pin the module with an extra LoadLibraryW reference",
    "cannot race the loader's final FreeLibrary-driven unload.",
    "LoadLibraryW(L\"acscmonitor.dll\");",
    "CreateThread(NULL, 0, Acscmonitor_LoadLibrary, (LPVOID)0, 0, NULL);",
    "CloseHandle(ThreadHandle);",
]:
    require(acsc, term, "Acscmonitor source")

for term in [
    "crashes firefox",
    "causing the crash",
    "prevent the library from ever being removed",
]:
    reject(acsc, term, "Acscmonitor source")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "### SREV-259: Custom Acscmonitor Loader Reference",
    "CUSTOM_ACSCMONITOR_LOADER_REFERENCE",
    "srev-259-custom-acscmonitor-loader-reference.schema.json",
    "Sandboxie/core/dll/custom.c",
    "Acscmonitor_LoadLibrary",
    "LoadLibraryW",
    "FreeLibrary",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-259 source gate passed")
