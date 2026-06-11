#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-227 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-227 failed: {label} still contains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-227-driver-registry-path-counted-copy.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-227 failed: schema is not draft-07")
if schema.get("id") != "DRIVER_REGISTRY_PATH_COUNTED_COPY":
    raise SystemExit("SREV-227 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "RegistryPath as a counted UNICODE_STRING",
    "save a copy of the registry path before DriverEntry returns",
    "Mem_AllocStringEx remains the owner for NUL terminated WCHAR pointer sources",
    "Mem_AllocUnicodeStringEx owns conversion from a counted UNICODE_STRING",
    "copies exactly UNICODE_STRING Length bytes and synthesizes the local NUL terminator",
]:
    require(contracts, term, "schema")

spec = (ROOT / "docs/plan/srev-227-driver-registry-path-counted-copy.md").read_text()
ledger = read_combined_ledger(ROOT)
mem_h = (ROOT / "Sandboxie/core/drv/mem.h").read_text()
mem_c = (ROOT / "Sandboxie/core/drv/mem.c").read_text()
driver_c = (ROOT / "Sandboxie/core/drv/driver.c").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

require(mem_h, "WCHAR *Mem_AllocUnicodeStringEx(", "mem.h declaration")
require(mem_h, "const UNICODE_STRING *model_string", "mem.h counted source")

helper = mem_c[
    mem_c.index("_FX WCHAR *Mem_AllocUnicodeStringEx"):
    mem_c.index("//---------------------------------------------------------------------------\n// Mem_FreeString")
]
for term in [
    "if (! model_string)\n        return NULL;",
    "if ((model_string->Length & (sizeof(WCHAR) - 1)) != 0)",
    "if (model_string->Length && (! model_string->Buffer))",
    "if (model_string->Length > (ULONG)-1 - sizeof(WCHAR))",
    "num_bytes = model_string->Length + sizeof(WCHAR);",
    "str = Mem_AllocEx(pool, num_bytes, InitMsg);",
    "memcpy(str, model_string->Buffer, model_string->Length);",
    "str[model_string->Length / sizeof(WCHAR)] = L'\\0';",
]:
    require(helper, term, "Mem_AllocUnicodeStringEx source shape")

driver_init = driver_c[
    driver_c.index("_FX NTSTATUS DriverEntry"):
    driver_c.index("// initialize simple utility modules")
]
require(
    driver_init,
    "Mem_AllocUnicodeStringEx(Driver_Pool, RegistryPath, TRUE);",
    "DriverEntry counted registry path copy",
)
reject(
    driver_init,
    "Mem_AllocStringEx(Driver_Pool, RegistryPath->Buffer, TRUE);",
    "old RegistryPath Buffer C-string copy",
)

for term in [
    "### SREV-227: Driver Registry Path Counted Copy",
    "DRIVER_REGISTRY_PATH_COUNTED_COPY",
    "srev-227-driver-registry-path-counted-copy.schema.json",
    "Sandboxie/core/drv/mem.c",
    "Sandboxie/core/drv/mem.h",
    "Sandboxie/core/drv/driver.c",
    "Mem_AllocUnicodeStringEx",
    "RegistryPath",
]:
    require(ledger, term, "ledger")

print("SREV-227 source gate passed")
