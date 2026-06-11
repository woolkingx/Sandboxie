#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-051 failed: {label} missing {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-051-dns-filter-csaddr-alignment.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-051 failed: schema is not draft-07")
if schema.get("id") != "DNS_FILTER_CSADDR_ALIGNMENT":
    raise SystemExit("SREV-051 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "WSAQUERYSETW.lpcsaBuffer points to a CSADDR_INFO array",
    "pointer-bearing SOCKET_ADDRESS members",
    "aligned to sizeof(void*) before assigning lpcsaBuffer",
    "required-size formula must include the same CSADDR_INFO alignment padding",
    "Runtime cursor alignment and size calculation alignment",
]:
    require(contracts, term, "schema")

src = (ROOT / "Sandboxie/core/dll/dns_filter.c").read_text()
spec = (ROOT / "docs/plan/srev-051-dns-filter-csaddr-alignment.md").read_text()
ledger = read_combined_ledger(ROOT)

for term in [
    "#define ALIGN_SIZE(size, align)",
    "neededSize = ALIGN_SIZE(neededSize, sizeof(void*));",
    "SIZE_T csaddrSize = (SIZE_T)ipCount * sizeof(CSADDR_INFO);",
    "// CSADDR_INFO array\n    currentPtr = ALIGN_UP(currentPtr, sizeof(void*));",
    "lpqsResults->lpcsaBuffer = (PCSADDR_INFO)currentPtr;",
]:
    require(src, term, "dns_filter source")

if src.index("neededSize = ALIGN_SIZE(neededSize, sizeof(void*));") > src.index("SIZE_T csaddrSize ="):
    raise SystemExit("SREV-051 failed: size alignment must precede csaddrSize")
if src.index("currentPtr = ALIGN_UP(currentPtr, sizeof(void*));") > src.index("lpqsResults->lpcsaBuffer ="):
    raise SystemExit("SREV-051 failed: cursor alignment must precede lpcsaBuffer")

for term in [
    "https://learn.microsoft.com/en-us/windows/win32/api/winsock2/ns-winsock2-wsaquerysetw",
    "https://learn.microsoft.com/en-us/windows/win32/api/ws2def/ns-ws2def-csaddr_info",
    "srev-051-dns-filter-csaddr-alignment.schema.json",
]:
    require(spec, term, "spec")

for term in [
    "### SREV-051: DNS Filter CSADDR_INFO Alignment",
    "DNS_FILTER_CSADDR_ALIGNMENT",
    "srev-051-dns-filter-csaddr-alignment.schema.json",
]:
    require(ledger, term, "ledger")

print("SREV-051 schema/source gate passed")
