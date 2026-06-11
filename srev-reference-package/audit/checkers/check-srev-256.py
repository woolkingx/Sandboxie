#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-256 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-256 failed: {label} still contains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-256-custom-comserver-broker-comment.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-256 failed: schema is not draft-07")
if schema.get("id") != "CUSTOM_COMSERVER_BROKER_COMMENT":
    raise SystemExit("SREV-256 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "brokered SbieSvc handoff",
    "pre-v4 direct COM IPC access",
    "broker topology rather than a generic workaround",
    "does not change process launch",
]:
    require(contracts, term, "schema")

source = (ROOT / "Sandboxie/core/dll/custom.c").read_text()
spec = (ROOT / "docs/plan/srev-256-custom-comserver-broker-comment.md").read_text()
srev_098 = (ROOT / "docs/plan/srev-098-ie-embedding-clsid-registry-policy.md").read_text()
srev_193 = (ROOT / "docs/plan/srev-193-ie-com-navigation-input-contract.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-256.md").read_text()

start = source.index("_FX void Custom_ComServer(void)")
end = source.index("WCHAR *cmdline;", start)
comserver = source[start:end]

for term in [
    "to serve the request, so Sandboxie uses a brokered COM handoff.",
    "version 4, the handoff granted the process full access",
    "the comserver",
    "module was moved into SbieSvc",
    "the simulated COM server is implemented in core/svc/comserver9.c",
]:
    require(comserver, term, "Custom_ComServer comment")

for term in [
    "so we need some workaround",
    "version 4, the workaround was",
    "to work around this, the comserver",
]:
    reject(comserver, term, "Custom_ComServer comment")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "LocalServer32",
    "local COM server",
]:
    require(srev_098, term, "SREV-098 adjacency")

for term in [
    "comserver9_ie.c",
    "IE COM server",
]:
    require(srev_193, term, "SREV-193 adjacency")

for term in [
    "### SREV-256: Custom COM Server Broker Comment",
    "CUSTOM_COMSERVER_BROKER_COMMENT",
    "srev-256-custom-comserver-broker-comment.schema.json",
    "Sandboxie/core/dll/custom.c",
    "Custom_ComServer",
    "SREV-098",
    "SREV-193",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-256 source gate passed")
