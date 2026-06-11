#!/usr/bin/env python3
import json
import re
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-190 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-190 failed: {label} still contains {needle!r}")


def slice_between(text: str, start: str, end: str) -> str:
    s = text.index(start)
    e = text.index(end, s)
    return text[s:e]


schema = json.loads(
    (ROOT / "docs/plan/srev-190-winsock-abi-function-pointer-contract.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-190 failed: schema is not draft-07")
if schema.get("id") != "WINSOCK_ABI_FUNCTION_POINTER_CONTRACT":
    raise SystemExit("SREV-190 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/dll/wsa_defs.h":
    raise SystemExit("SREV-190 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "dynamic function pointer ABI declarations",
    "detour entry points installed through SBIEDLL_HOOK",
    "must use WSAAPI",
    "must use WINAPI",
    "must return SOCKET not int",
    "must return void",
    "writable output address pointer",
    "must return BOOL",
    "return FALSE not SOCKET_ERROR",
    "x86 and x64 Windows",
]:
    require(contracts, term, "schema contracts")

wsa_defs = (ROOT / "Sandboxie/core/dll/wsa_defs.h").read_text()
net = (ROOT / "Sandboxie/core/dll/net.c").read_text()
spec = (ROOT / "docs/plan/srev-190-winsock-abi-function-pointer-contract.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-190.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "#ifndef WSAAPI\n#define WSAAPI WINAPI\n#endif",
    "typedef int (WSAAPI *P_WSAStartup)(",
    "typedef int (WSAAPI *P_WSACleanup)(void);",
    "typedef SOCKET (WSAAPI *P_socket)(",
    "typedef int (WSAAPI *P_WSAIoctl)(",
    "typedef SOCKET (WSAAPI *P_WSASocketW)(",
    "typedef void (WSAAPI *P_WSASetLastError)(int err);",
    "typedef int (WSAAPI *P_getsockname)(",
    "    void           *name,",
    "typedef BOOL (WSAAPI *P_ConnectEx) (",
    "typedef BOOL (WSAAPI *P_AcceptEx)(",
    "typedef PCSTR (WSAAPI *P_inet_ntop)(",
    "typedef ULONG (WINAPI *P_GetAdaptersAddresses)(",
]:
    require(wsa_defs, term, "wsa_defs ABI")

for bad in [
    "typedef int (*P_WSAStartup)(",
    "typedef int (*P_socket)(",
    "typedef int (*P_WSASocketW)(",
    "typedef int (*P_WSASetLastError)(int err);",
    "const void     *name,\n    int            *namelen);",
    "typedef int (*P_ConnectEx)",
]:
    reject(wsa_defs, bad, "wsa_defs old ABI")

if re.search(r"typedef\s+(?:int|SOCKET|BOOL|void|PCSTR|ULONG)\s+\(\*P_", wsa_defs):
    raise SystemExit("SREV-190 failed: unannotated function pointer typedef remains in wsa_defs.h")

for term in [
    "static int WSAAPI WSA_WSAStartup(",
    "static int WSAAPI WSA_WSAIoctl(",
    "static SOCKET WSAAPI WSA_WSASocketW(",
    "static int WSAAPI WSA_bind(",
    "static int WSAAPI WSA_connect(",
    "static int WSAAPI WSA_WSAConnect(",
    "static BOOL WSAAPI WSA_ConnectEx(",
    "static int WSAAPI WSA_sendto(",
    "static int WSAAPI WSA_WSASendTo(",
    "static int WSAAPI WSA_recvfrom(",
    "static int WSAAPI WSA_WSARecvFrom(",
    "static int WSAAPI WSA_closesocket(SOCKET s);",
    "_FX int WSAAPI WSA_WSAStartup(",
    "_FX int WSAAPI WSA_WSAIoctl(",
    "static SOCKET WSAAPI WSA_WSASocketW(",
    "_FX int WSAAPI WSA_bind(",
    "_FX int WSAAPI WSA_connect(",
    "_FX int WSAAPI WSA_WSAConnect(",
    "_FX BOOL WSAAPI WSA_ConnectEx(",
    "_FX int WSAAPI WSA_sendto(",
    "_FX int WSAAPI WSA_WSASendTo(",
    "_FX int WSAAPI WSA_recvfrom(",
    "_FX int WSAAPI WSA_WSARecvFrom(",
    "_FX int WSAAPI WSA_closesocket(SOCKET s)",
]:
    require(net, term, "net detour ABI")

connect_ex = slice_between(
    net,
    "_FX BOOL WSAAPI WSA_ConnectEx(",
    "/*\n//---------------------------------------------------------------------------\n// WSA_listen",
)
for term in [
    "return FALSE;",
    "BOOL ret = __sys_ConnectEx(",
    "return ret == SOCKS_SUCCESS;",
    "return ret;",
]:
    require(connect_ex, term, "ConnectEx return shape")
reject(connect_ex, "return SOCKET_ERROR;", "ConnectEx boolean failure path")

for term in [
    "kind: srev-ledger-entry",
    "id: SREV-190",
    "owner: Sandboxie/core/dll/wsa_defs.h",
    "spec: docs/plan/srev-190-winsock-abi-function-pointer-contract.md",
    "schema: docs/plan/srev-190-winsock-abi-function-pointer-contract.schema.json",
    "checker: docs/plan/check-srev-190.py",
]:
    require(ledger_fragment, term, "ledger fragment header")

for term in [
    "### SREV-190: Winsock ABI Function Pointer Contract",
    "WINSOCK_ABI_FUNCTION_POINTER_CONTRACT",
    "Sandboxie/core/dll/wsa_defs.h",
    "Sandboxie/core/dll/net.c",
    "WSAAPI",
    "ConnectEx",
]:
    require(ledger, term, "combined ledger")

print("SREV-190 schema/source gate passed")
