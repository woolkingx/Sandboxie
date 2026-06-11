#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-204 failed: {label} missing {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-204-htiface7-ie-com-abi-boundary.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-204 failed: schema is not draft-07")
if schema.get("id") != "HTIFACE7_IE_COM_ABI_BOUNDARY":
    raise SystemExit("SREV-204 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/svc/htiface7.h":
    raise SystemExit("SREV-204 failed: wrong owner")
if schema.get("consumer") != "Sandboxie/core/svc/comserver9_ie.c":
    raise SystemExit("SREV-204 failed: wrong consumer")

contracts = "\n".join(schema["contracts"])
for term in [
    "external IE COM ABI projection",
    "not Protected Storage or credential-store data",
    "SREV-193 is the active consumer fix",
    "intentionally makes no source mutation",
]:
    require(contracts, term, "schema contract")

header = (ROOT / "Sandboxie/core/svc/htiface7.h").read_text()
include_owner = (ROOT / "Sandboxie/core/svc/comserver9.c").read_text()
consumer = (ROOT / "Sandboxie/core/svc/comserver9_ie.c").read_text()
spec = (ROOT / "docs/plan/srev-204-htiface7-ie-com-abi-boundary.md").read_text()
srev193 = (ROOT / "docs/plan/srev-193-ie-com-navigation-input-contract.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-204.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "typedef interface IUri IUri;",
    "Uri_PROPERTY_PASSWORD",
    "HRESULT ( STDMETHODCALLTYPE *GetRawUri )",
    "typedef interface ITargetFramePriv2 ITargetFramePriv2;",
    "ITargetFramePriv2_AggregatedNavigation2",
]:
    require(header, term, "htiface7 ABI token")

require(include_owner, "#include \"htiface7.h\"", "header include owner")
for term in [
    "IEServer_ITargetFramePriv2_AggregatedNavigation2",
    "IUri_GetRawUri(pUri, &pszUrl)",
    "ITargetFramePriv2_NavigateHack(",
]:
    require(consumer, term, "consumer coordinate")

for term in [
    "Reject a NULL `IUri *` before calling `IUri_GetRawUri`.",
    "Release the `IUri::GetRawUri` output with `SysFreeString`.",
]:
    require(srev193, term, "SREV-193 consumer gate")

for term in [
    "kind: srev-ledger-entry",
    "id: SREV-204",
    "owner: Sandboxie/core/svc/htiface7.h",
    "consumer: Sandboxie/core/svc/comserver9_ie.c",
    "spec: docs/plan/srev-204-htiface7-ie-com-abi-boundary.md",
    "schema: docs/plan/srev-204-htiface7-ie-com-abi-boundary.schema.json",
    "checker: docs/plan/check-srev-204.py",
    "classified source-level; no local mutation",
]:
    require(ledger_fragment, term, "ledger fragment")
    require(ledger, term, "combined ledger")

print("SREV-204 source gate passed")
