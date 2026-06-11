#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-050 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-050 failed: {label} still contains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-050-dns-filter-response-buffer.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-050 failed: schema is not draft-07")
if schema.get("id") != "DNS_FILTER_WSAQUERYSET_RESPONSE_BUFFER":
    raise SystemExit("SREV-050 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "caller-provided output buffer",
    "required size on WSAEFAULT",
    "packed WSAQUERYSETW response layout",
    "gated against bufferEnd in release builds",
    "final sanity check is diagnostic only",
    "relative offsets from the HOSTENT base",
]:
    require(contracts, term, "schema")

src = (ROOT / "Sandboxie/core/dll/dns_filter.c").read_text()
spec = (ROOT / "docs/plan/srev-050-dns-filter-response-buffer.md").read_text()
ledger = read_combined_ledger(ROOT)

for term in [
    "#define CHECK_BUFFER_SPACE(ptr, size, end)",
    "BYTE* _ptr = (BYTE*)(ptr);",
    "BYTE* _end = (BYTE*)(end);",
    "SIZE_T _size = (SIZE_T)(size);",
    "if (_ptr > _end || _size > (SIZE_T)(_end - _ptr))",
    "SetLastError(WSAEFAULT);",
    "return FALSE;",
    "BYTE* bufferEnd = (BYTE*)lpqsResults + *lpdwBufferLength;",
    "SREV-050 owns this diagnostic end fence.",
    "gates are the release-mode overflow boundary before each write.",
    "if ((BYTE*)currentPtr > bufferEnd)",
]:
    require(src, term, "dns_filter source")

for term in [
    "// Debug buffer bounds checking (only in debug builds)",
    "#ifdef _DEBUG\n#define CHECK_BUFFER_SPACE",
    "#else\n#define CHECK_BUFFER_SPACE(ptr, size, end) ((void)0)",
    "#ifdef _DEBUG\n    // Debug: set buffer end for bounds checking",
    "This is a lightweight failsafe in case size calculations were wrong",
    "if ((BYTE*)currentPtr > ((BYTE*)lpqsResults + *lpdwBufferLength))",
]:
    reject(src, term, "dns_filter source")

for term in [
    "https://learn.microsoft.com/en-us/windows/win32/api/winsock2/nf-winsock2-wsalookupservicenextw",
    "https://learn.microsoft.com/en-us/windows/win32/api/winsock2/ns-winsock2-wsaquerysetw",
    "https://learn.microsoft.com/en-us/windows/win32/api/winsock2/ns-winsock2-blob",
    "srev-050-dns-filter-response-buffer.schema.json",
    "SREV-263",
    "diagnostic final-fence ownership",
]:
    require(spec, term, "spec")

for term in [
    "### SREV-050: DNS Filter Response Buffer Gates",
    "DNS_FILTER_WSAQUERYSET_RESPONSE_BUFFER",
    "srev-050-dns-filter-response-buffer.schema.json",
    "SREV-263",
]:
    require(ledger, term, "ledger")

print("SREV-050 schema/source gate passed")
