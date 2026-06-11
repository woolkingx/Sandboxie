#!/usr/bin/env python3
import json
import re
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-175 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-175 failed: stale {label} still present")


def macro_value(text: str, name: str) -> str:
    match = re.search(rf"^#define\s+{re.escape(name)}\s+([^\s]+)", text, re.MULTILINE)
    if not match:
        raise SystemExit(f"SREV-175 failed: macro {name} missing")
    return match.group(1)


schema = json.loads((ROOT / "docs/plan/srev-175-api-flags-single-source.schema.json").read_text())
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-175 failed: schema is not draft-07")
if schema.get("id") != "DRIVER_API_FLAG_SINGLE_SOURCE":
    raise SystemExit("SREV-175 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "api_flags.h owns Sandboxie driver API flag constants",
    "configuration query flags are cross-boundary wire flags not private conf.h implementation constants",
    "conf.h consumes CONF_GET flags by including api_flags.h and must not duplicate their numeric definitions",
    "Microsoft-owned duplicate options remain named in api_flags.h with documented DuplicateHandle and ZwDuplicateObject values",
    "Sandboxie-only duplicate routing bits remain above the documented low option bits and are stripped before native ZwDuplicateObject calls",
    "resource monitor process reload and feature flags are unchanged",
    "SREV-175 does not change any numeric flag value caller behavior config query expansion semantics handle duplication routing monitor logging process info reporting reload behavior or driver feature reporting",
    "Linux source gate is not Windows build runtime proof",
]:
    require(contracts, term, "schema")

api_flags_h = (ROOT / "Sandboxie/core/drv/api_flags.h").read_text()
conf_h = (ROOT / "Sandboxie/core/drv/conf.h").read_text()
conf_c = (ROOT / "Sandboxie/core/drv/conf.c").read_text()
ipc_c = (ROOT / "Sandboxie/core/drv/ipc.c").read_text()
secure_c = (ROOT / "Sandboxie/core/dll/secure.c").read_text()
spec = (ROOT / "docs/plan/srev-175-api-flags-single-source.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-175.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

expected_values = {
    "CONF_GET_NO_GLOBAL": "0x40000000L",
    "CONF_GET_NO_EXPAND": "0x20000000L",
    "CONF_GET_NO_TEMPLS": "0x10000000L",
    "DUPLICATE_CLOSE_SOURCE": "0x00000001",
    "DUPLICATE_SAME_ACCESS": "0x00000002",
    "DUPLICATE_SAME_ATTRIBUTES": "0x00000004",
    "DUPLICATE_INHERIT": "0x00040000",
    "DUPLICATE_INTO_OTHER": "0x00080000",
    "MONITOR_TYPE_MASK": "0x000000FF",
    "SBIE_FLAG_VALID_PROCESS": "0x00000001",
    "SBIE_CONF_FLAG_RECONFIGURE": "0x00000001",
    "SBIE_FEATURE_FLAG_WFP": "0x00000001",
}
for name, value in expected_values.items():
    actual = macro_value(api_flags_h, name)
    if actual != value:
        raise SystemExit(f"SREV-175 failed: {name} expected {value}, got {actual}")

require(conf_h, '#include "api_flags.h"', "conf.h api_flags include")
for name in ["CONF_GET_NO_GLOBAL", "CONF_GET_NO_EXPAND", "CONF_GET_NO_TEMPLS"]:
    reject(conf_h, f"#define {name}", f"conf.h duplicate {name}")
    require(conf_c, name, f"conf.c consumes {name}")

for term in [
    "Options &= ~DUPLICATE_INHERIT;",
    "Options &= ~DUPLICATE_INTO_OTHER;",
    "Options & ~DUPLICATE_CLOSE_SOURCE",
]:
    require(ipc_c, term, "driver duplicate custom flag stripping")

for term in [
    "Options |= DUPLICATE_INTO_OTHER;",
    "Options |= DUPLICATE_INHERIT;",
    "SbieApi_DuplicateObject(",
]:
    require(secure_c, term, "dll duplicate routing")

for term in [
    "### SREV-175: Driver API Flag Single Source",
    "DRIVER_API_FLAG_SINGLE_SOURCE",
    "srev-175-api-flags-single-source.schema.json",
    "Sandboxie/core/drv/api_flags.h",
    "Sandboxie/core/drv/conf.h",
    "CONF_GET_NO_GLOBAL",
    "Driver API Flag Single Source",
    "Windows driver",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-175 schema/source gate passed")
