#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-319 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-319 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-319-winsock-socket-wfp-prompt-boundary.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-319 failed: schema is not draft-07")
if schema.get("id") != "WINSOCK_SOCKET_WFP_PROMPT_BOUNDARY":
    raise SystemExit("SREV-319 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/dll/net.c":
    raise SystemExit("SREV-319 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "WSASocketW creation result remains provider-owned",
    "PromptForInternetAccess may request a manual bypass before socket creation",
    "SbieApi_CheckInternetAccess owns the driver internet-access state query",
    "File_InternetBlockade_ManualBypass owns the interactive box-manager request",
    "WFP driver filtering owns blocked-traffic enforcement after socket creation",
    "changes comments and proof only",
]:
    require(contracts, term, "schema contracts")

net = (ROOT / "Sandboxie/core/dll/net.c").read_text()
file_pipe = (ROOT / "Sandboxie/core/dll/file_pipe.c").read_text()
sbieapi = (ROOT / "Sandboxie/core/dll/sbieapi.c").read_text()
spec = (ROOT / "docs/plan/srev-319-winsock-socket-wfp-prompt-boundary.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-319.md").read_text()
srev_190 = (ROOT / "docs/plan/ledger/srev-190.md").read_text()
srev_190_check = (ROOT / "docs/plan/check-srev-190.py").read_text()
srev_239 = (ROOT / "docs/plan/ledger/srev-239.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

ws_start = net.index("static SOCKET WSAAPI WSA_WSASocketW(")
ws_end = net.index("// WSA_HandleAfUnix", ws_start)
ws = net[ws_start:ws_end]

for term in [
    "if (WSA_WFPisBlocking) {",
    "BOOLEAN prompt = SbieApi_QueryConfBool(NULL, L\"PromptForInternetAccess\", FALSE);",
    "SbieApi_CheckInternetAccess(0, NULL, !prompt) == STATUS_ACCESS_DENIED",
    "&& (!prompt || !File_InternetBlockade_ManualBypass())) {",
    "SREV-319: socket creation remains provider-owned.",
    "Prompt/manual-bypass only updates driver internet-access state;",
    "the WFP driver enforces blocked traffic after the socket exists.",
    "WSA_WFPisBlocking = FALSE;",
    "SOCKET s = __sys_WSASocketW(af, type, protocol, lpProtocolInfo, g, dwFlags);",
    "if (WSA_ProxyHack || WSA_BindIP)\n        WSA_GetSock(s, TRUE)->af = af;",
    "return s;",
]:
    require(ws, term, "WSA_WSASocketW source")

for stale in [
    "we always allow",
    "to not make the process crash or behave unexpectedly",
    "we don't care for the result",
]:
    reject(ws, stale, "WSA_WSASocketW compatibility comment")

for term in [
    "WSA_WFPisEnabled = (Dll_DriverFlags & SBIE_FEATURE_FLAG_WFP) != 0;",
    "WSA_WFPisBlocking = !Config_GetSettingsForImageName_bool(L\"AllowNetworkAccess\", TRUE);",
    "else // load rules only when the driver is not doing the filtering",
]:
    require(net, term, "WSA_Init source")

for term in [
    "_FX const BOOLEAN File_InternetBlockade_ManualBypass()",
    "req.msgid = MAN_INET_BLOCKADE;",
    "rpl = SbieDll_CallServerQueue(INTERACTIVE_QUEUE_NAME, &req, sizeof(req), sizeof(*rpl));",
    "Dll_RefreshPathList();",
]:
    require(file_pipe, term, "manual bypass source")

for term in [
    "_FX LONG SbieApi_CheckInternetAccess(",
    "API_CHECK_INTERNET_ACCESS_ARGS *args =",
    "args->func_code               = API_CHECK_INTERNET_ACCESS;",
    "status = SbieApi_Ioctl(parms);",
]:
    require(sbieapi, term, "SbieApi_CheckInternetAccess source")

for term in [
    "WINSOCK_ABI_FUNCTION_POINTER_CONTRACT",
    "`socket` and `WSASocketW` return `SOCKET`",
]:
    require(srev_190, term, "SREV-190 adjacency")
require(srev_190_check, "static SOCKET WSAAPI WSA_WSASocketW(", "SREV-190 checker adjacency")

for term in [
    "WFP_DRIVER_HEADER_TOPOLOGY_CONTRACT",
    "WFP_classify block/permit decision",
    "runtime behavior remains covered by existing and future concrete-owner SREV Windows gates",
]:
    require(srev_239, term, "SREV-239 adjacency")

for term in [
    "WINSOCK_SOCKET_WFP_PROMPT_BOUNDARY",
    "socket creation remains provider-owned",
    "No source behavior changed",
    "SREV-190 owns the ABI shape",
    "SREV-239 owns the driver WFP module topology",
]:
    require(spec, term, "spec")

for term in [
    "kind: srev-ledger-entry",
    "id: SREV-319",
    "owner: Sandboxie/core/dll/net.c",
    "spec: docs/plan/srev-319-winsock-socket-wfp-prompt-boundary.md",
    "schema: docs/plan/srev-319-winsock-socket-wfp-prompt-boundary.schema.json",
    "checker: docs/plan/check-srev-319.py",
]:
    require(ledger_fragment, term, "ledger fragment header")

for term in [
    "### SREV-319: Winsock Socket WFP Prompt Boundary",
    "WINSOCK_SOCKET_WFP_PROMPT_BOUNDARY",
    "Sandboxie/core/dll/net.c",
    "WSASocketW",
    "File_InternetBlockade_ManualBypass",
]:
    require(ledger, term, "combined ledger")

print("SREV-319 schema/source gate passed")
