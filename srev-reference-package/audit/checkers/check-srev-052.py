#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-052 failed: {label} missing {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-052-dns-filter-ip-entry-ownership.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-052 failed: schema is not draft-07")
if schema.get("id") != "DNS_FILTER_IP_ENTRY_OWNERSHIP":
    raise SystemExit("SREV-052 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "owns IP_ENTRY allocation",
    "_inet_xton returns 1 only for a valid parsed IPv4 or IPv6 address",
    "transfers ownership to the entries list",
    "invalid IP_ENTRY remains owned by the parser and must be freed",
    "IPv4-mapped IPv6 synthetic entry transfers ownership only after successful allocation",
]:
    require(contracts, term, "schema")

src = (ROOT / "Sandboxie/core/dll/dns_filter.c").read_text()
spec = (ROOT / "docs/plan/srev-052-dns-filter-ip-entry-ownership.md").read_text()
ledger = read_combined_ledger(ROOT)

start = src.index("_FX BOOLEAN WSA_InitNetDnsFilter(")
end = src.index("// WSA_WSALookupServiceBeginW", start)
init = src[start:end]

for term in [
    "IP_ENTRY* entry = (IP_ENTRY*)Dll_Alloc(sizeof(IP_ENTRY));",
    "if (!entry)\n                    continue;",
    "if (_inet_xton(ip_str1, ip_len1, &entry->IP, &entry->Type) == 1)",
    "List_Insert_After(entries, NULL, entry);",
    "else {\n                    Dll_Free(entry);\n                }",
    "IP_ENTRY* entry6 = (IP_ENTRY*)Dll_Alloc(sizeof(IP_ENTRY));",
    "if (!entry6)\n                        continue;",
]:
    require(init, term, "WSA_InitNetDnsFilter")

for term in [
    "https://learn.microsoft.com/en-us/windows/win32/api/ws2tcpip/nf-ws2tcpip-inetptonw",
    "srev-052-dns-filter-ip-entry-ownership.schema.json",
]:
    require(spec, term, "spec")

for term in [
    "### SREV-052: DNS Filter IP Entry Ownership",
    "DNS_FILTER_IP_ENTRY_OWNERSHIP",
    "srev-052-dns-filter-ip-entry-ownership.schema.json",
]:
    require(ledger, term, "ledger")

print("SREV-052 schema/source gate passed")
