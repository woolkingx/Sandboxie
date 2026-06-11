#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-320 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-320 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-320-proc-child-token-compatibility-gates.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-320 failed: schema is not draft-07")
if schema.get("id") != "PROC_CHILD_TOKEN_COMPATIBILITY_GATES":
    raise SystemExit("SREV-320 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/dll/proc.c":
    raise SystemExit("SREV-320 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "caller default token shape or an explicit primary token shape",
    "hToken clearing is a process-token selection boundary",
    "Edge CDM token clearing stays under DeprecatedTokenHacks",
    "Firefox token clearing stays under DLL_IMAGE_MOZILLA_FIREFOX",
    "plugin-container and Acrobat token clearing stays under DropChildProcessToken",
    "changes comments and proof only",
]:
    require(contracts, term, "schema contracts")

proc = (ROOT / "Sandboxie/core/dll/proc.c").read_text()
spec = (ROOT / "docs/plan/srev-320-proc-child-token-compatibility-gates.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-320.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

start = proc.index("_FX BOOL Proc_CreateProcessInternalW(")
end = proc.index("// use a copy path for the current directory", start)
create_token_block = proc[start:end]

for term in [
    "SREV-320: legacy Edge CDM service child token gate.",
    "Existing predicate only clears hToken for service-sandbox-type.",
    "if (Config_GetSettingsForImageName_bool(L\"DeprecatedTokenHacks\", FALSE))",
    "Dll_ImageType == DLL_IMAGE_GOOGLE_CHROME && lpCommandLine",
    "wcsistr(lpCommandLine, L\"--service-sandbox-type\")",
    "hToken = NULL;",
    "SREV-320: Firefox sandboxingKind child token gate.",
    "Existing predicate only clears hToken for this launch marker.",
    "Dll_ImageType == DLL_IMAGE_MOZILLA_FIREFOX && lpCommandLine",
    "wcsistr(lpCommandLine, L\"-sandboxingKind\")",
    "SREV-320: plugin sandbox child token gate.",
    "Existing image/config predicates clear hToken for this legacy path.",
    "Config_GetSettingsForImageName_bool(L\"DropChildProcessToken\", FALSE)",
    "Dll_ImageType == DLL_IMAGE_ACROBAT_READER",
    "Dll_ImageType == DLL_IMAGE_PLUGIN_CONTAINER",
]:
    require(create_token_block, term, "Proc_CreateProcessInternalW token block")

for stale in [
    "MSEdge Compatibility hack",
    "Compatibility hack for Firefox 106.x",
    "hack:  recent versions of Flash Player",
]:
    reject(create_token_block, stale, "Proc_CreateProcessInternalW token comment")

for term in [
    "PROC_CHILD_TOKEN_COMPATIBILITY_GATES",
    "`CreateProcessInternalW` is not the public Microsoft API contract",
    "process-token selection boundary",
    "No token value, condition, command-line predicate, image predicate",
]:
    require(spec, term, "spec")

for term in [
    "kind: srev-ledger-entry",
    "id: SREV-320",
    "owner: Sandboxie/core/dll/proc.c",
    "spec: docs/plan/srev-320-proc-child-token-compatibility-gates.md",
    "schema: docs/plan/srev-320-proc-child-token-compatibility-gates.schema.json",
    "checker: docs/plan/check-srev-320.py",
]:
    require(ledger_fragment, term, "ledger fragment header")

for term in [
    "### SREV-320: Proc Child Token Compatibility Gates",
    "PROC_CHILD_TOKEN_COMPATIBILITY_GATES",
    "DeprecatedTokenHacks",
    "DropChildProcessToken",
    "service-sandbox-type",
    "-sandboxingKind",
]:
    require(ledger, term, "combined ledger")

print("SREV-320 schema/source gate passed")
