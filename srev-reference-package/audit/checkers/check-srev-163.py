#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-163 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-163 failed: {label} still contains {needle!r}")


def section(text: str, start: str, end: str) -> str:
    start_index = text.index(start)
    end_index = text.index(end, start_index)
    return text[start_index:end_index]


schema = json.loads((ROOT / "docs/plan/srev-163-socks5-byte-string-gates.schema.json").read_text())
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-163 failed: schema is not draft-07")
if schema.get("id") != "SOCKS5_BYTE_STRING_GATES":
    raise SystemExit("SREV-163 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "proxy.c owns SOCKS5 protocol frame construction",
    "SOCKS_AUTH_MAX_SIZE is a protocol byte maximum not a null-terminated WCHAR storage size",
    "local credential text buffers need SOCKS_AUTH_MAX_SIZE + 1 WCHAR slots",
    "wcstombs conversion failure is not a legal SOCKS5 field length",
    "SOCKS username and password byte fields must be between 1 and 255 bytes after conversion before writing ULEN or PLEN",
    "SOCKS domain names must be between 1 and 255 bytes before writing the one-byte domain length",
    "Linux source gate is not Windows networking runtime proof",
]:
    require(contracts, term, "schema")

proxy = (ROOT / "Sandboxie/core/dll/proxy.c").read_text()
net = (ROOT / "Sandboxie/core/dll/net.c").read_text()
spec = (ROOT / "docs/plan/srev-163-socks5-byte-string-gates.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-163.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "#define SOCKS_AUTH_MAX_SIZE         255",
    "#define SOCKS_AUTH_TEXT_SIZE        (SOCKS_AUTH_MAX_SIZE + 1)",
    "static BOOLEAN socks5_auth_field_to_bytes(",
    "static BOOLEAN socks5_request_add_domain(",
]:
    require(proxy, term, "proxy constants/helpers")

auth_helper = section(proxy, "_FX BOOLEAN socks5_auth_field_to_bytes", "_FX BOOLEAN socks5_handshake")
for term in [
    "required_len = wcstombs(NULL, text, 0);",
    "required_len == (size_t)-1",
    "required_len == 0",
    "required_len > SOCKS_AUTH_MAX_SIZE",
    "converted_len = wcstombs(bytes, text, required_len);",
    "if (converted_len != required_len)",
    "*bytes_len = converted_len;",
]:
    require(auth_helper, term, "auth helper")

handshake = section(proxy, "_FX BOOLEAN socks5_handshake", "//---------------------------------------------------------------------------\n// socks5_request_send")
for term in [
    "char l[SOCKS_AUTH_MAX_SIZE];",
    "char p[SOCKS_AUTH_MAX_SIZE];",
    "if (! socks5_auth_field_to_bytes(login, l, &login_len) ||",
    "! socks5_auth_field_to_bytes(pass, p, &pass_len))",
    "auth_buf[offset++] = login_len;",
    "auth_buf[offset++] = (char)pass_len;",
]:
    require(handshake, term, "handshake")
reject(handshake, "size_t login_len = wcstombs", "unchecked login conversion")
reject(handshake, "size_t pass_len = wcstombs", "unchecked password conversion")

domain_helper = section(proxy, "_FX BOOLEAN socks5_request_add_domain", "_FX char socks5_request")
for term in [
    "size_t domain_len = strlen(domain);",
    "if (domain_len == 0 || domain_len > 255)",
    "*(*ptr)++ = SOCKS_DOMAINNAME;",
    "*(*ptr)++ = (char)domain_len;",
    "memcpy(*ptr, domain, domain_len);",
    "*ptr += domain_len;",
]:
    require(domain_helper, term, "domain helper")

request = section(proxy, "_FX char socks5_request", "//---------------------------------------------------------------------------\n// RELAY_CONFIG")
for term in [
    "if (! socks5_request_add_domain(&ptr, domain))",
    "return SOCKS_GENERAL_FAILURE;",
]:
    require(request, term, "request domain gate")
reject(request, "*ptr++ = strlen(domain);", "truncated domain length write")
reject(request, "memcpy(ptr, domain, strlen(domain));", "ungated domain copy")

relay = section(proxy, "typedef struct {", "//---------------------------------------------------------------------------\n// run_relay_loop")
require(relay, "WCHAR login[SOCKS_AUTH_TEXT_SIZE];", "relay login text storage")
require(relay, "WCHAR pass[SOCKS_AUTH_TEXT_SIZE];", "relay password text storage")

start_relay = section(proxy, "USHORT start_socks5_relay", "fail:")
for term in [
    "WCHAR login[SOCKS_AUTH_TEXT_SIZE]",
    "WCHAR pass[SOCKS_AUTH_TEXT_SIZE]",
    "if (! login || ! pass)",
    "wcscpy_s(relay_config->login, SOCKS_AUTH_TEXT_SIZE, login) != 0",
    "wcscpy_s(relay_config->pass, SOCKS_AUTH_TEXT_SIZE, pass) != 0",
]:
    require(start_relay, term, "relay copy gate")

net_struct = section(net, "struct NETPROXY_RULE {", "};")
require(net_struct, "WCHAR   login[256];", "NETPROXY_RULE login storage")
require(net_struct, "WCHAR   pass[256];", "NETPROXY_RULE password storage")

parse_proxy = section(net, "BOOLEAN WSA_ParseNetProxy", "//---------------------------------------------------------------------------\n// WSA_InitNetProxy")
for term in [
    "if (login_len > 255)",
    "wmemcpy(proxy->login, login_value, login_len);",
    "proxy->login[login_len] = L'\\0';",
    "if (pass_len > 255)",
    "proxy->pass[pass_len] = L'\\0';",
]:
    require(parse_proxy, term, "NetworkUseProxy credential gate")

for term in [
    "### SREV-163: SOCKS5 Byte String Gates",
    "SOCKS5_BYTE_STRING_GATES",
    "srev-163-socks5-byte-string-gates.schema.json",
    "Sandboxie/core/dll/proxy.c",
    "Sandboxie/core/dll/net.c",
    "socks5_auth_field_to_bytes",
    "socks5_request_add_domain",
    "SOCKS_AUTH_TEXT_SIZE",
    "proxy->login[login_len] = L'\\0';",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-163 schema/source gate passed")
