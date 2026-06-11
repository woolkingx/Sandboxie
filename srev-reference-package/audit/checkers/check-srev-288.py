#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-288 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-288 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-288-gdi-getstockobject-seh-failure-result.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-288 failed: schema is not draft-07")
if schema.get("id") != "GDI_GETSTOCKOBJECT_SEH_FAILURE_RESULT":
    raise SystemExit("SREV-288 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/dll/gdi.c":
    raise SystemExit("SREV-288 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "GetStockObject returns a stock-object handle on success and NULL on failure",
    "Gdi_GetStockObject owns only the exception-to-NULL boundary around the native GetStockObject call",
    "the hook is registered only from full GDI initialization after GetProcAddress resolves GetStockObject",
    "SEH must remain narrow around __sys_GetStockObject(fnObject)",
    "this SREV changes comments and proof only",
]:
    require(contracts, term, "schema")

source = (ROOT / "Sandboxie/core/dll/gdi.c").read_text()
spec = (ROOT / "docs/plan/srev-288-gdi-getstockobject-seh-failure-result.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-288.md").read_text()

init_start = source.index("_FX BOOLEAN Gdi_Full_Init_impl(")
init_end = source.index("//---------------------------------------------------------------------------\n// Gdi_Init_Spool", init_start)
init_block = source[init_start:init_end]

for term in [
    "if (full) {\n\t\tGetStockObject = (P_GetStockObject)\n\t\t\tGetProcAddress(module, \"GetStockObject\");",
    "if (full) {\n\t\tSBIEDLL_HOOK(Gdi_, GetStockObject);\n\t}",
]:
    require(init_block, term, "full GDI hook topology")

func_start = source.index("_FX HGDIOBJ Gdi_GetStockObject(")
func_end = source.index("//---------------------------------------------------------------------------\n// Gdi_InitDCCache", func_start)
func = source[func_start:func_end]
comment_start = source.index("// SREV-288: gdi32full GetStockObject")
comment = source[comment_start:func_start]

for term in [
    "SREV-288: gdi32full GetStockObject is hooked only in full GDI init.",
    "Chrome's sandbox is still initializing",
    "GDI shared state",
    "documented GetStockObject failure result:",
    "NULL. Keep the SEH guard narrow around the native GetStockObject call.",
]:
    require(comment, term, "source comment")

for term in [
    "HGDIOBJ rc = 0;",
    "__try {\n        rc = __sys_GetStockObject(fnObject);\n    }",
    "__except (EXCEPTION_EXECUTE_HANDLER) {\n        rc = 0;\n    }",
    "return rc;",
]:
    require(func, term, "Gdi_GetStockObject source")

for stale in [
    "Workaround for a rare chrome crash",
    "cause a crash",
    "there is no error handling",
    "deeper problem",
    "high entropy ASLR",
]:
    reject(comment + func, stale, "Gdi_GetStockObject comment")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "GDI_GETSTOCKOBJECT_SEH_FAILURE_RESULT",
    "GetStockObject",
    "SYSTEM_FONT",
    "EXCEPTION_EXECUTE_HANDLER",
    "NULL failure result",
    "No hook registration, exception filter, return value, or stock-object selector",
]:
    require(spec, term, "spec")

for term in [
    "### SREV-288: GDI GetStockObject SEH Failure Result",
    "GDI_GETSTOCKOBJECT_SEH_FAILURE_RESULT",
    "srev-288-gdi-getstockobject-seh-failure-result.schema.json",
    "Sandboxie/core/dll/gdi.c",
    "Gdi_GetStockObject",
    "GetStockObject",
    "EXCEPTION_EXECUTE_HANDLER",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-288 source gate passed")
