#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-138 failed: {label} missing {needle!r}")


schema = json.loads((ROOT / "docs/plan/srev-138-alpc-local-header-contract.schema.json").read_text())
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-138 failed: schema is not draft-07")
if schema.get("id") != "ALPC_LOCAL_HEADER_CONTRACT":
    raise SystemExit("SREV-138 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "alpc.h is a local ABI header and not the authoritative Windows ALPC schema",
    "private-research-derived",
    "must keep shared ALPC constants and structure field names in sync",
    "PORT_MESSAGE remains the local carrier header",
    "MAX_PORTMSG_LENGTH remains 328",
    "Endpoint policy may read payload bytes only after validating the PORT_MESSAGE header",
    "Changes to ALPC_MESSAGE_VIEW or ALPC flags require Windows runtime capture",
    "runtime capture must prove the local header mirror",
    "SREV-015 and SREV-138 share docs/plan/srev-015-138-alpc-runtime-capture.schema.json",
]:
    require(contracts, term, "schema")

matrix = "\n".join(
    "\n".join(value) if isinstance(value, list) else str(value)
    for value in schema["runtime_capture_matrix"].values()
)
for term in [
    "supported Windows 10 x86",
    "supported Windows 10 x64",
    "supported Windows 11 x64",
    "supported Windows 11 ARM64 where built",
    "sizeof(PORT_MESSAGE)",
    "sizeof(ALPC_PORT_ATTRIBUTES)",
    "sizeof(ALPC_MESSAGE_VIEW)",
    "FIELD_OFFSET values",
    "NtCreatePort",
    "NtAlpcConnectPort",
    "NtAlpcSendWaitReceivePort",
    "PipeServer.cpp old LPC request/reply",
    "namedpipeserver.cpp ALPC connect",
    "dll/ipc.c ALPC send/wait/receive",
    "ipc_port.c driver endpoint policy",
    "MAX_PORTMSG_LENGTH boundary",
    "ALPC_PORT_ATTRIBUTES.Flags",
    "ALPC_MESSAGE_VIEW.SendFlags",
    "ALPC_MESSAGE_VIEW.ReceiveFlags",
    "ALPC_MESSAGE_FLAG_VIEW mapped-view path",
    "LSA RPC endpoint traffic",
    "SAM RPC endpoint traffic",
    "spooler RPC endpoint traffic",
    "dynamic RPC port traffic",
    "malformed short payloads",
    "message longer than MAX_PORTMSG_LENGTH",
    "TotalLength below sizeof(PORT_MESSAGE)",
    "unknown ALPC_MESSAGE_VIEW flags outside the accepted mask",
    "mirror-header sizeof or FIELD_OFFSET drift",
]:
    require(matrix, term, "schema runtime capture matrix")

alpc = (ROOT / "Sandboxie/core/drv/alpc.h").read_text()
ntddk = (ROOT / "Sandboxie/common/win32_ntddk.h").read_text()
spec = (ROOT / "docs/plan/srev-138-alpc-local-header-contract.md").read_text()
shared_playbook = (ROOT / "docs/plan/srev-015-138-alpc-runtime-capture-playbook.md").read_text()
shared_schema = json.loads((ROOT / "docs/plan/srev-015-138-alpc-runtime-capture.schema.json").read_text())
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-138.md").read_text()

if shared_schema.get("id") != "ALPC_RUNTIME_CAPTURE_EVIDENCE":
    raise SystemExit("SREV-138 failed: shared ALPC capture schema has wrong id")
require(shared_playbook, "SREV-138 must be interpreted before SREV-015", "shared capture playbook")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for text, label in [(alpc, "alpc.h"), (ntddk, "win32_ntddk.h")]:
    for term in [
        "#define MAX_PORTMSG_LENGTH 328",
        "typedef struct _PORT_MESSAGE",
        "USHORT DataLength;",
        "USHORT TotalLength;",
        "USHORT Type;",
        "USHORT DataInfoOffset;",
        "CLIENT_ID ClientId;",
        "ULONG MessageId;",
        "ULONG_PTR ClientViewSize;",
        "ULONG CallbackId;",
        "typedef struct _PORT_DATA_INFO",
        "typedef struct _ALPC_PORT_ATTRIBUTES",
        "SECURITY_QUALITY_OF_SERVICE SecurityQos;",
        "ULONG       MaxMessageLength;",
        "typedef struct _ALPC_MESSAGE_VIEW",
        "ULONG       ReplyLength;",
        "ULONG       MessageId;",
        "ULONG       CallbackId;",
        "ULONG_PTR   ViewBase;",
        "ULONG       ViewSize;",
        "#define PORT_INFO_CANIMPERSONATE        0x010000",
        "#define ALPC_SYNC_CONNECTION            0x020000",
        "#define ALPC_MESSAGE_FLAG_VIEW          0x40000000",
        "LPC-ALPC-paper.pdf",
        "SREV-138: private local ALPC ABI mirror",
        "require Windows capture before changing fields, widths, or flags",
    ]:
        require(text, term, label)

for term in [
    "__declspec(dllimport) NTSTATUS NtCreatePort",
    "__declspec(dllimport) NTSTATUS NtConnectPort",
    "__declspec(dllimport) NTSTATUS NtSecureConnectPort",
    "__declspec(dllimport) NTSTATUS NtRequestWaitReplyPort",
    "__declspec(dllimport) NTSTATUS NtReplyWaitReceivePort",
    "__declspec(dllimport) NTSTATUS NtImpersonateClientOfPort",
    "NTOS_NTSTATUS   LpcRequestPort",
    "extern POBJECT_TYPE *LpcPortObjectType;",
]:
    require(alpc, term, "alpc.h native declarations")

svc_pipe = (ROOT / "Sandboxie/core/svc/PipeServer.cpp").read_text()
svc_named = (ROOT / "Sandboxie/core/svc/namedpipeserver.cpp").read_text()
dll_ipc = (ROOT / "Sandboxie/core/dll/ipc.c").read_text()
drv_ipc_port = (ROOT / "Sandboxie/core/drv/ipc_port.c").read_text()
drv_obj_flt = (ROOT / "Sandboxie/core/drv/obj_flt.c").read_text()
srev015 = (ROOT / "docs/plan/srev-015-alpc-connect-flags.md").read_text()

for term in [
    "#define MSG_DATA_LEN            (MAX_PORTMSG_LENGTH - sizeof(PORT_MESSAGE))",
    "NtCreatePort(",
    "MAX_PORTMSG_LENGTH",
    "NtReplyWaitReceivePort(hReplyPort, &PortContext, ReplyMsg, msg)",
    "NtImpersonateClientOfPort(",
]:
    require(svc_pipe, term, "PipeServer.cpp call sites")

for term in [
    "ALPC_PORT_ATTRIBUTES alpc;",
    "alpc.Flags = PORT_INFO_CANIMPERSONATE;",
    "ALPC_SYNC_CONNECTION",
    "ALPC_MESSAGE_VIEW view;",
    "ALPC_MESSAGE_FLAG_VIEW",
    "PORT_DATA_INFO *info",
    "NtRequestWaitReplyPort(",
]:
    require(svc_named, term, "namedpipeserver.cpp call sites")

for term in [
    "ALPC_PORT_ATTRIBUTES *AlpcConnectInfo",
    "ALPC_MESSAGE_VIEW *SendView",
    "ALPC_MESSAGE_VIEW *ReceiveView",
    "RequestMsg->u2.s2.DataInfoOffset",
    "memcpy(req->data, RequestMsg, MAX_PORTMSG_LENGTH);",
    "memcpy(req->data, SendMsg, SendMsg->u1.s1.TotalLength);",
    "ReceiveView->u.s1.CallbackId  = msg->CallbackId;",
]:
    require(dll_ipc, term, "dll/ipc.c call sites")

for term in [
    "ProbeForRead(msg, sizeof(PORT_MESSAGE), sizeof(ULONG_PTR));",
    "ULONG  len = msg->u1.s1.DataLength;",
    "UCHAR* ptr = (UCHAR*)((UCHAR*)msg + sizeof(PORT_MESSAGE));",
    "Ipc_GetRpcMsgId",
]:
    require(drv_ipc_port, term, "drv/ipc_port.c call sites")

for term in [
    "proper  IPC isolation requires filtering of NtRequestPort, NtRequestWaitReplyPort, and NtAlpcSendWaitReceivePort calls",
]:
    require(drv_obj_flt, term, "drv/obj_flt.c IPC isolation comment")

for term in [
    "## Local Shape",
    "official Microsoft DDI",
    "PORT_INFO_CANIMPERSONATE",
    "ALPC_SYNC_CONNECTION",
    "ALPC_MESSAGE_FLAG_VIEW",
]:
    require(srev015, term, "SREV-015 precedent")

for term in [
    "### SREV-138: ALPC Local Header Contract",
    "ALPC_LOCAL_HEADER_CONTRACT",
    "srev-138-alpc-local-header-contract.schema.json",
    "srev-015-138-alpc-runtime-capture.schema.json",
    "LPC-ALPC-paper.pdf",
    "Runtime Capture Matrix",
    "concrete runtime capture matrix",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-138 schema/source gate passed")
