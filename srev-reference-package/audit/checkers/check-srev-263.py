#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-263 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-263 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-263-dns-filter-final-fence-owner.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-263 failed: schema is not draft-07")
if schema.get("id") != "DNS_FILTER_FINAL_FENCE_OWNER":
    raise SystemExit("SREV-263 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/dll/dns_filter.c":
    raise SystemExit("SREV-263 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "SREV-050 owns the response buffer capacity contract",
    "CHECK_BUFFER_SPACE gates each release-mode segment write against bufferEnd",
    "final end check is diagnostic only",
    "does not change response layout required-size calculation",
]:
    require(contracts, term, "schema")

src = (ROOT / "Sandboxie/core/dll/dns_filter.c").read_text()
srev_050 = (ROOT / "docs/plan/srev-050-dns-filter-response-buffer.md").read_text()
srev_050_check = (ROOT / "docs/plan/check-srev-050.py").read_text()
spec = (ROOT / "docs/plan/srev-263-dns-filter-final-fence-owner.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-263.md").read_text()

start = src.index("_FX BOOLEAN WSA_FillResponseStructure(")
end = src.index("//---------------------------------------------------------------------------\n// WSA_InitNetDnsFilter", start)
func = src[start:end]

for term in [
    "BYTE* bufferEnd = (BYTE*)lpqsResults + *lpdwBufferLength;",
    "CHECK_BUFFER_SPACE(currentPtr, domainNameLen, bufferEnd);",
    "CHECK_BUFFER_SPACE(currentPtr, csaddrSize, bufferEnd);",
    "CHECK_BUFFER_SPACE(currentPtr, sizeof(SOCKADDR_IN) * 2, bufferEnd);",
    "CHECK_BUFFER_SPACE(currentPtr, sizeof(SOCKADDR_IN6_LH) * 2, bufferEnd);",
    "CHECK_BUFFER_SPACE(currentPtr, sizeof(BLOB) + blobSize, bufferEnd);",
    "SREV-050 owns this diagnostic end fence.",
    "gates are the release-mode overflow boundary before each write.",
    "if ((BYTE*)currentPtr > bufferEnd)",
]:
    require(func, term, "WSA_FillResponseStructure")

for stale in [
    "This is a lightweight failsafe in case size calculations were wrong",
    "if ((BYTE*)currentPtr > ((BYTE*)lpqsResults + *lpdwBufferLength))",
]:
    reject(func, stale, "WSA_FillResponseStructure")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "Before SREV-263",
    "diagnostic final-fence ownership",
    "same `bufferEnd` owner",
]:
    require(srev_050, term, "SREV-050 spec adjacency")

for term in [
    "SREV-050 owns this diagnostic end fence.",
    "gates are the release-mode overflow boundary before each write.",
    "if ((BYTE*)currentPtr > bufferEnd)",
    "SREV-263",
]:
    require(srev_050_check, term, "SREV-050 checker adjacency")

for term in [
    "### SREV-263: DNS Filter Final Fence Owner",
    "DNS_FILTER_FINAL_FENCE_OWNER",
    "srev-263-dns-filter-final-fence-owner.schema.json",
    "Sandboxie/core/dll/dns_filter.c",
    "WSA_FillResponseStructure",
    "SREV-050",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-263 source gate passed")
