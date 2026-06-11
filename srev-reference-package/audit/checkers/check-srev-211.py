#!/usr/bin/env python3
import json
from pathlib import Path

from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-211 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-211 failed: stale {label} remains {needle!r}")


def between(text: str, start: str, end: str) -> str:
    a = text.index(start)
    b = text.index(end, a + len(start))
    return text[a:b]


schema = json.loads(
    (ROOT / "docs/plan/srev-211-icmp-echo-failure-reply-contract.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-211 failed: schema is not draft-07")
if schema.get("id") != "ICMP_ECHO_FAILURE_REPLY_CONTRACT":
    raise SystemExit("SREV-211 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/svc/iphlpserver.h":
    raise SystemExit("SREV-211 failed: wrong owner")
if schema.get("implementation") != "Sandboxie/core/svc/iphlpserver.cpp":
    raise SystemExit("SREV-211 failed: wrong implementation")
if schema.get("wire") != "Sandboxie/core/svc/iphlpwire.h":
    raise SystemExit("SREV-211 failed: wrong wire contract")

contracts = "\n".join(schema["contracts"])
for term in [
    "service broker declaration boundary",
    "ICMP echo API call and reply normalization logic",
    "NULL state before LoadLibrary",
    "return of zero is an error path",
    "zero replies, and zero reply bytes",
    "pointer normalization runs only for successful replies",
]:
    require(contracts, term, "schema contract")

spec = (ROOT / "docs/plan/srev-211-icmp-echo-failure-reply-contract.md").read_text()
header = (ROOT / "Sandboxie/core/svc/iphlpserver.h").read_text()
src = (ROOT / "Sandboxie/core/svc/iphlpserver.cpp").read_text()
wire = (ROOT / "Sandboxie/core/svc/iphlpwire.h").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-211.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "class IpHlpServer",
    "MSG_HEADER *SendEchoHandler(MSG_HEADER *msg, HANDLE idProcess);",
    "void *m_IcmpSendEcho2;",
    "void *m_IcmpSendEcho2Ex;",
    "void *m_Icmp6SendEcho2;",
]:
    require(header, term, "iphlpserver declaration boundary")

for term in [
    "struct tagIPHLP_SEND_ECHO_REQ",
    "ULONG reply_size;",
    "ULONG request_size;",
    "struct tagIPHLP_SEND_ECHO_RPL",
    "ULONG num_replies;",
    "UCHAR reply_data[1];",
]:
    require(wire, term, "wire reply topology")

ctor = between(
    src,
    "IpHlpServer::IpHlpServer(PipeServer *pipeServer)",
    "//---------------------------------------------------------------------------\n// CloseCallback",
)
for term in [
    "m_IcmpCreateFile  = NULL;",
    "m_Icmp6CreateFile = NULL;",
    "m_IcmpCloseHandle = NULL;",
    "m_IcmpSendEcho2   = NULL;",
    "m_IcmpSendEcho2Ex = NULL;",
    "m_Icmp6SendEcho2  = NULL;",
    "m_IcmpSendEcho2   = GetProcAddress(_iphlpapi, \"IcmpSendEcho2\");",
    "m_IcmpSendEcho2Ex = GetProcAddress(_iphlpapi, \"IcmpSendEcho2Ex\");",
    "m_Icmp6SendEcho2  = GetProcAddress(_iphlpapi, \"Icmp6SendEcho2\");",
]:
    require(ctor, term, "dynamic API pointer initialization")

send = between(
    src,
    "MSG_HEADER *IpHlpServer::SendEchoHandler(MSG_HEADER *msg, HANDLE idProcess)",
    "//---------------------------------------------------------------------------\n// NotifyHandler",
)
for term in [
    "if (num_replies == 0) {\n            rpl->h.status = GetLastError();\n            reply_size = 0;\n        } else\n            rpl->h.status = ERROR_SUCCESS;",
    "if ((! req->ip6) && rpl->h.status == ERROR_SUCCESS && num_replies) {",
    "rpl->num_replies = num_replies;",
    "rpl->reply_size = reply_size;",
]:
    require(send, term, "ICMP failure reply contract")

reject(send, "num_replies = 1; // even on error we need to return one valid result buffer", "fake one-reply error path")
reject(send, "if ((! req->ip6) && num_replies) {", "error-path IPv4 pointer rewrite")

if not send.index("rpl->h.status = GetLastError();") < send.index("reply_size = 0;"):
    raise SystemExit("SREV-211 failed: reply_size is not cleared after API failure status")
if not send.index("if (num_replies == 0)") < send.index("if ((! req->ip6) && rpl->h.status == ERROR_SUCCESS"):
    raise SystemExit("SREV-211 failed: success gate appears before API return classification")

for term in [
    "kind: srev-ledger-entry",
    "id: SREV-211",
    "owner: Sandboxie/core/svc/iphlpserver.h",
    "implementation: Sandboxie/core/svc/iphlpserver.cpp",
    "wire: Sandboxie/core/svc/iphlpwire.h",
    "spec: docs/plan/srev-211-icmp-echo-failure-reply-contract.md",
    "schema: docs/plan/srev-211-icmp-echo-failure-reply-contract.schema.json",
    "checker: docs/plan/check-srev-211.py",
    "patched source-level after official ICMP echo failure shape review",
]:
    require(ledger_fragment, term, "ledger fragment")
    require(ledger, term, "combined ledger")

print("SREV-211 source gate passed")
