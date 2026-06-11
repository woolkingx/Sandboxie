#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-053 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-053 failed: {label} still contains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-053-dns-filter-begin-constructor.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-053 failed: schema is not draft-07")
if schema.get("id") != "DNS_FILTER_BEGIN_CONSTRUCTOR":
    raise SystemExit("SREV-053 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "returns only a handle used by later WSALookupServiceNext calls",
    "requires a non-null lphLookup before publishing a fake lookup handle",
    "owns DomainName and optional ServiceClassId",
    "fake lookup handle crosses the API boundary only after",
    "SOCKET_ERROR with WSA_NOT_ENOUGH_MEMORY",
    "removes any inserted WSA_LookupMap state",
]:
    require(contracts, term, "schema")

src = (ROOT / "Sandboxie/core/dll/dns_filter.c").read_text()
my_wsa = (ROOT / "Sandboxie/common/my_wsa.h").read_text()
spec = (ROOT / "docs/plan/srev-053-dns-filter-begin-constructor.md").read_text()
ledger = read_combined_ledger(ROOT)

start = src.index("_FX int WSA_WSALookupServiceBeginW(")
end = src.index("// WSA_WSALookupServiceNextW", start)
begin = src[start:end]

for term in [
    "lpqsRestrictions->lpszServiceInstanceName && lphLookup",
    "if (!path_lwr) {\n            SetLastError(WSA_NOT_ENOUGH_MEMORY);",
    "if (!fakeHandle) {\n                Dll_Free(path_lwr);\n                SetLastError(WSA_NOT_ENOUGH_MEMORY);",
    "WSA_LOOKUP* pLookup = WSA_GetLookup(fakeHandle, TRUE);",
    "if (!pLookup) {\n                Dll_Free(fakeHandle);\n                Dll_Free(path_lwr);",
    "if (!pLookup->DomainName) {\n                map_remove(&WSA_LookupMap, fakeHandle);",
    "if (!pLookup->ServiceClassId) {\n                    Dll_Free(pLookup->DomainName);\n                    map_remove(&WSA_LookupMap, fakeHandle);",
    "PVOID* aux = Pattern_Aux(found);",
    "pLookup->NoMore = TRUE;",
    "*lphLookup = fakeHandle;",
]:
    require(begin, term, "WSA_WSALookupServiceBeginW")

reject(
    begin,
    "*lphLookup = fakeHandle;\n\n            WSA_LOOKUP* pLookup = WSA_GetLookup(fakeHandle, TRUE);",
    "WSA_WSALookupServiceBeginW",
)
reject(begin, "SetLastError(ERROR_NOT_ENOUGH_MEMORY);", "WSA_WSALookupServiceBeginW")
require(my_wsa, "#define WSA_NOT_ENOUGH_MEMORY   ERROR_NOT_ENOUGH_MEMORY", "Winsock memory error fallback")

publish = begin.index("*lphLookup = fakeHandle;")
for earlier in [
    "wcscpy_s(pLookup->DomainName",
    "PVOID* aux = Pattern_Aux(found);",
]:
    if begin.index(earlier) > publish:
        raise SystemExit(f"SREV-053 failed: handle published before {earlier}")

for term in [
    "https://learn.microsoft.com/en-us/windows/win32/api/winsock2/nf-winsock2-wsalookupservicebeginw",
    "https://learn.microsoft.com/en-us/windows/win32/api/winsock2/ns-winsock2-wsaquerysetw",
    "srev-053-dns-filter-begin-constructor.schema.json",
]:
    require(spec, term, "spec")

for term in [
    "### SREV-053: DNS Filter Begin Constructor Boundary",
    "DNS_FILTER_BEGIN_CONSTRUCTOR",
    "srev-053-dns-filter-begin-constructor.schema.json",
]:
    require(ledger, term, "ledger")

print("SREV-053 schema/source gate passed")
