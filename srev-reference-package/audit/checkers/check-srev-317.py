#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-317 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-317 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-317-ldr-third-party-module-callback-group.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-317 failed: schema is not draft-07")
if schema.get("id") != "LDR_THIRD_PARTY_MODULE_CALLBACK_GROUP":
    raise SystemExit("SREV-317 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/dll/ldr.c":
    raise SystemExit("SREV-317 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "Ldr_Dlls owns only loaded module base-name to init-callback registration",
    "the non-Microsoft group label must not imply one shared vendor behavior owner",
    "Acscmonitor_Init behavior remains owned by SREV-259",
    "Custom_Avast_SnxHk behavior remains owned by SREV-257",
    "Custom_SYSFER_DLL behavior remains owned by SREV-055 and SREV-258",
    "DigitalGuardian_Init behavior remains owned by SREV-088 and SREV-249",
    "comment only",
]:
    require(contracts, term, "schema")

ldr = (ROOT / "Sandboxie/core/dll/ldr.c").read_text()
spec = (ROOT / "docs/plan/srev-317-ldr-third-party-module-callback-group.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-317.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

start = ldr.index("// SREV-317: non-Microsoft module callback registration group.")
end = ldr.index("{ NULL,                     NULL,                           0}", start)
group = ldr[start:end]
for term in [
    "// SREV-317: non-Microsoft module callback registration group.",
    "#ifndef _M_ARM64",
    "// Non Microsoft DLLs:",
    "{ L\"acscmonitor.dll\",       Acscmonitor_Init,               0},",
    "{ L\"IDMIECC.dll\",           Custom_InternetDownloadManager, 0},",
    "{ L\"snxhk.dll\",             Custom_Avast_SnxHk,             0},",
    "{ L\"snxhk64.dll\",           Custom_Avast_SnxHk,             0},",
    "{ L\"sysfer.dll\",            Custom_SYSFER_DLL,              0},",
    "#ifdef _WIN64",
    "{ L\"dgapi64.dll\",           DigitalGuardian_Init,           0},",
    "#else",
    "{ L\"dgapi.dll\",             DigitalGuardian_Init,           0},",
]:
    require(group, term, "loader group")
reject(group, "$Workaround$ - 3rd party fix", "loader group label")

for entry, target in [
    ("SREV-259", "CUSTOM_ACSCMONITOR_LOADER_REFERENCE"),
    ("SREV-257", "CUSTOM_AVAST_TRAMPOLINE_PUBLISH_GATE"),
    ("SREV-055", "CUSTOM_SYSFER_ENTRYPOINT_PATCH"),
    ("SREV-258", "CUSTOM_SYSFER_COMMENT_OWNER"),
    ("SREV-088", "DLL_DIGITALGUARDIAN_MODULE_FLAG"),
    ("SREV-249", "DIGITALGUARDIAN_COMMENT_TOPOLOGY"),
]:
    fragment = (ROOT / f"docs/plan/ledger/{entry.lower()}.md").read_text()
    require(fragment, target, f"{entry} adjacency")
    require(spec, entry, "spec adjacency")
    require(spec, target, "spec adjacency")

for term in [
    "LDR_THIRD_PARTY_MODULE_CALLBACK_GROUP",
    "loaded module base-name to init-callback registration",
    "non-Microsoft module callback registration group",
    "No DLL name, callback function, ARM64",
    "Runtime gate: no runtime gate is required",
]:
    require(spec, term, "spec")

for term in [
    "### SREV-317: Ldr Third-Party Module Callback Group",
    "LDR_THIRD_PARTY_MODULE_CALLBACK_GROUP",
    "srev-317-ldr-third-party-module-callback-group.schema.json",
    "Sandboxie/core/dll/ldr.c",
    "Ldr_Dlls",
    "Acscmonitor_Init",
    "Custom_Avast_SnxHk",
    "Custom_SYSFER_DLL",
    "DigitalGuardian_Init",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-317 source gate passed")
