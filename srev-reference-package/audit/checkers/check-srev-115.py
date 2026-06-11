#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-115 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-115 failed: {label} still contains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-115-my-winnt-warning-boundary.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-115 failed: schema is not draft-07")
if schema.get("id") != "MY_WINNT_WARNING_BOUNDARY":
    raise SystemExit("SREV-115 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "driver-wide NT compatibility shim",
    "private NT structure declarations are compatibility data shapes",
    "suppress C4267 only for declarations inside the header",
    "warning-state mutation introduced by the header is restored",
    "does not cross into includer code",
    "must not change private NT structure layouts",
]:
    require(contracts, term, "schema")

source = (ROOT / "Sandboxie/core/drv/my_winnt.h").read_text()
spec = (ROOT / "docs/plan/srev-115-my-winnt-warning-boundary.md").read_text()
ledger = read_combined_ledger(ROOT)

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "#ifndef _MY_WINNT_H",
    "#define _MY_WINNT_H",
    "#pragma warning(push)",
    "#pragma warning(disable : 4267)",
    "#include <ntifs.h>",
    "#include \"alpc.h\"",
    "typedef struct _OBJECT_TYPE",
    "typedef struct _OBJECT_HEADER",
    "typedef struct _SYSTEM_PROCESS_INFORMATION",
    "typedef struct _SYSTEM_MODULE_INFORMATION",
    "ZwQuerySystemInformation(",
    "#pragma warning(pop)",
    "#endif",
]:
    require(source, term, "my_winnt.h")

push_idx = source.index("#pragma warning(push)")
disable_idx = source.index("#pragma warning(disable : 4267)")
pop_idx = source.rindex("#pragma warning(pop)")
endif_idx = source.rindex("#endif")
if not (push_idx < disable_idx < pop_idx < endif_idx):
    raise SystemExit("SREV-115 failed: warning push/disable/pop order is wrong")
if source[pop_idx:].strip() != "#pragma warning(pop)\n\n#endif":
    raise SystemExit("SREV-115 failed: warning pop is not the include-guard tail")

if source.count("#pragma warning(push)") != 1:
    raise SystemExit("SREV-115 failed: expected one warning push")
if source.count("#pragma warning(pop)") != 1:
    raise SystemExit("SREV-115 failed: expected one warning pop")

reject(source[pop_idx:], "#pragma warning(disable : 4267)", "C4267 suppression after pop")

for term in [
    "### SREV-115: My WinNT Warning Boundary",
    "MY_WINNT_WARNING_BOUNDARY",
    "srev-115-my-winnt-warning-boundary.schema.json",
    "Sandboxie/core/drv/my_winnt.h",
    "#pragma warning(push)",
    "#pragma warning(pop)",
    "C4267",
]:
    require(ledger, term, "ledger")

print("SREV-115 schema/source gate passed")
