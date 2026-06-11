#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-144 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-144 failed: {label} still contains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-144-iphlp-send-echo-payload-boundary.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-144 failed: schema is not draft-07")
if schema.get("id") != "IPHLP_SEND_ECHO_PAYLOAD_BOUNDARY":
    raise SystemExit("SREV-144 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "iphlpserver.cpp owns service-side validation of the IP Helper ICMP echo pipe request before any Microsoft ICMP API receives caller-supplied bytes",
    "IPHLP_SEND_ECHO_REQ.request_data is a counted variable payload owned by request_size, not by the fixed struct size alone",
    "The service accepts a SendEcho request only when req->h.length is at least the fixed request size, request_size <= 0xFFFF, reply_size <= 0x0FFFFF, and FIELD_OFFSET(IPHLP_SEND_ECHO_REQ, request_data) + request_size <= req->h.length",
    "RequestSize passed to IcmpSendEcho2, IcmpSendEcho2Ex, and Icmp6SendEcho2 remains a WORD derived from the already-bounded request_size",
    "reply_size allocation and WOW64 reply widening stay unchanged",
    "Proxy handle lookup, IP version matching, network access policy, and restricted-token ICMP handle creation stay unchanged",
]:
    require(contracts, term, "schema")

iphlpserver = (ROOT / "Sandboxie/core/svc/iphlpserver.cpp").read_text()
iphlpwire = (ROOT / "Sandboxie/core/svc/iphlpwire.h").read_text()
iphlp_client = (ROOT / "Sandboxie/core/dll/iphlp.c").read_text()
spec = (ROOT / "docs/plan/srev-144-iphlp-send-echo-payload-boundary.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-144.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "struct tagIPHLP_SEND_ECHO_REQ",
    "BOOLEAN iswow64;",
    "BOOLEAN ip6;",
    "BOOLEAN ex2;",
    "ULONG handle;",
    "ULONG timeout;",
    "UCHAR src_addr[32];",
    "UCHAR dst_addr[32];",
    "ULONG reply_size;",
    "ULONG request_size;",
    "UCHAR request_data[1];",
    "struct tagIPHLP_SEND_ECHO_RPL",
    "UCHAR reply_data[1];",
]:
    require(iphlpwire, term, "wire packet shape")

for term in [
    "len = sizeof(IPHLP_SEND_ECHO_REQ) + RequestSize;",
    "req = Dll_Alloc(len);",
    "req->h.length = len;",
    "req->h.msgid = MSGID_IPHLP_SEND_ECHO;",
    "req->reply_size = ReplySize;",
    "req->request_size = RequestSize;",
    "memcpy(&req->request_data, RequestData, req->request_size);",
    "rpl = (IPHLP_SEND_ECHO_RPL *)SbieDll_CallServer(&req->h);",
]:
    require(iphlp_client, term, "DLL client packet construction")

func_start = iphlpserver.index("MSG_HEADER *IpHlpServer::SendEchoHandler")
func_end = iphlpserver.index("//---------------------------------------------------------------------------\n// NotifyHandler", func_start)
send_echo = iphlpserver[func_start:func_end]
for term in [
    "IPHLP_SEND_ECHO_REQ *req = (IPHLP_SEND_ECHO_REQ *)msg;",
    "if (req->h.length < sizeof(IPHLP_SEND_ECHO_REQ))",
    "if ((req->request_size > 0xFFFF) || (req->reply_size > 0x0FFFFF))",
    "ULONG offset = FIELD_OFFSET(IPHLP_SEND_ECHO_REQ, request_data);",
    "if (offset + req->request_size > req->h.length)",
    "return SHORT_REPLY(ERROR_INVALID_PARAMETER);",
    "m_ProxyHandle->Find(idProcess, req->handle);",
    "int ipver = req->ip6 ? 6 : 4;",
    "if (ipver != ProxyIcmp->ipver)",
    "void *p_IcmpSendEcho = m_IcmpSendEcho2;",
    "p_IcmpSendEcho = m_Icmp6SendEcho2;",
    "p_IcmpSendEcho = m_IcmpSendEcho2Ex;",
    "ULONG reply_size = req->reply_size;",
    "if (req->iswow64 && reply_size == 0x1C + req->request_size)",
    "reply_size = 0x28 + req->request_size;",
    "WORD RequestSize = (WORD)req->request_size;",
    "req->request_data, RequestSize, pRequestOptions,",
    "m_ProxyHandle->Release(ProxyIcmp);",
]:
    require(send_echo, term, "service SendEcho boundary")

if send_echo.index("ULONG offset = FIELD_OFFSET(IPHLP_SEND_ECHO_REQ, request_data);") > send_echo.index("m_ProxyHandle->Find(idProcess, req->handle);"):
    raise SystemExit("SREV-144 failed: payload validation occurs after proxy handle lookup")
if send_echo.index("ULONG offset = FIELD_OFFSET(IPHLP_SEND_ECHO_REQ, request_data);") > send_echo.index("WORD RequestSize = (WORD)req->request_size;"):
    raise SystemExit("SREV-144 failed: payload validation occurs after RequestSize conversion")

reject(send_echo, "FIELD_OFFSET(QUEUE_PUTREQ_REQ, data)", "copied queue packet offset")

for term in [
    "Sandboxie/core/svc/iphlpserver.cpp",
    "Sandboxie/core/svc/iphlpwire.h",
    "Sandboxie/core/dll/iphlp.c",
    "### SREV-144: IP Helper SendEcho Payload Boundary",
    "IPHLP_SEND_ECHO_PAYLOAD_BOUNDARY",
    "srev-144-iphlp-send-echo-payload-boundary.schema.json",
    "FIELD_OFFSET(IPHLP_SEND_ECHO_REQ, request_data)",
    "offset + req->request_size > req->h.length",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-144 schema/source gate passed")
