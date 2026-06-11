#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-068 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-068 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-068-winsock-proxy-sockaddr-gate.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-068 failed: schema is not draft-07")
if schema.get("id") != "WINSOCK_PROXY_SOCKADDR_GATE":
    raise SystemExit("SREV-068 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "sockaddr pointer plus namelen byte count",
    "first u_short in a valid sockaddr is the address family",
    "AF_INET may be locally interpreted only when namelen is at least sizeof(SOCKADDR_IN)",
    "AF_INET6 may be locally interpreted only when namelen is at least sizeof(SOCKADDR_IN6_LH)",
    "must not enter Sandboxie proxy routing",
    "fall through to the underlying Winsock API",
    "unsupported-family fallback comments must name the SREV-068 local interpretation gate",
]:
    require(contracts, term, "schema")

src = (ROOT / "Sandboxie/core/dll/net.c").read_text()
spec = (ROOT / "docs/plan/srev-068-winsock-proxy-sockaddr-gate.md").read_text()
ledger = read_combined_ledger(ROOT)

getip_start = src.index("_FX BOOLEAN WSA_GetIP(")
getip_end = src.index("// WSA_IsConnectSockaddr", getip_start)
getip_func = src[getip_start:getip_end]

gate_start = src.index("_FX BOOLEAN WSA_IsConnectSockaddr(")
gate_end = src.index("// WSA_IsLocalhostAddress", gate_start)
gate_func = src[gate_start:gate_end]

localhost_start = src.index("_FX BOOLEAN WSA_IsLocalhostAddress(")
localhost_end = src.index("// WSA_DumpIP", localhost_start)
localhost_func = src[localhost_start:localhost_end]

bypass_start = src.index("_FX BOOLEAN WSA_BypassProxy(")
bypass_end = src.index("// WSA_GetProxy", bypass_start)
bypass_func = src[bypass_start:bypass_end]

proxy_start = src.index("_FX BOOLEAN WSA_GetProxy(")
proxy_end = src.index("// WSA_begin_connect", proxy_start)
proxy_func = src[proxy_start:proxy_end]

for term in [
    "if (!addr || !pIP || addrlen < sizeof(USHORT))\n        return FALSE;",
    "else // SREV-068: unsupported or malformed family is not locally interpreted.\n        return FALSE;",
]:
    require(getip_func, term, "WSA_GetIP source")
reject(getip_func, "something's wrong", "WSA_GetIP generic fallback comment")

for term in [
    "if (!addr || addrlen < (int)sizeof(USHORT))\n        return FALSE;",
    "family = ((const SOCKADDR*)addr)->sa_family;",
    "if (family == AF_INET) {\n        if (addrlen < (int)sizeof(SOCKADDR_IN))\n            return FALSE;",
    "else if (family == AF_INET6) {\n        if (addrlen < (int)sizeof(SOCKADDR_IN6_LH))\n            return FALSE;",
    "if (af)\n        *af = family;",
]:
    require(gate_func, term, "WSA_IsConnectSockaddr source")

for term in [
    "if (!WSA_IsConnectSockaddr(addr, addrlen, &af))\n        return FALSE;",
    "((const SOCKADDR_IN*)addr)->sin_addr.S_un.S_un_b.s_b1 == 127",
    "memcmp(ip, loop6, sizeof(loop6)) == 0",
    "ip[10] == 0xff && ip[11] == 0xff &&\n                ip[12] == 127",
]:
    require(localhost_func, term, "WSA_IsLocalhostAddress source")

for func_name, func in [
    ("WSA_BypassProxy", bypass_func),
    ("WSA_GetProxy", proxy_func),
]:
    require(func, "if (!WSA_IsConnectSockaddr(addr, addrlen, &af))\n        return FALSE;", f"{func_name} source")
    if "name->sa_family" in func:
        raise SystemExit(f"SREV-068 failed: raw sa_family dereference remains in {func_name}")

proxy_gate = (
    "if (WSA_ProxyEnabled && WSA_IsConnectSockaddr(name, namelen, NULL) &&\n"
    "            !WSA_IsLocalhostAddress(name, namelen) && !WSA_BypassProxy(name, namelen))"
)
if src.count(proxy_gate) != 3:
    raise SystemExit("SREV-068 failed: connect-family proxy gates are not all guarded")

if "is_localhost(name)" in src:
    raise SystemExit("SREV-068 failed: unresolved is_localhost(name) remains")

for term in [
    "https://learn.microsoft.com/en-us/windows/win32/api/winsock2/nf-winsock2-connect",
    "https://learn.microsoft.com/en-us/windows/win32/api/winsock2/nf-winsock2-wsaconnect",
    "https://learn.microsoft.com/en-us/windows/win32/api/mswsock/nc-mswsock-lpfn_connectex",
    "https://learn.microsoft.com/en-us/windows/win32/winsock/sockaddr-2",
    "srev-068-winsock-proxy-sockaddr-gate.schema.json",
    "unsupported-family fallback comment now names this SREV-068",
]:
    require(spec, term, "spec")

for term in [
    "### SREV-068: Winsock Proxy Sockaddr Gate",
    "WINSOCK_PROXY_SOCKADDR_GATE",
    "srev-068-winsock-proxy-sockaddr-gate.schema.json",
    "unsupported-family fallback comment",
]:
    require(ledger, term, "ledger")

print("SREV-068 schema/source gate passed")
