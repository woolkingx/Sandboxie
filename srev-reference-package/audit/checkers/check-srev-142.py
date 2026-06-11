#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-142 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-142 failed: {label} still contains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-142-queue-putreq-event-handle-ownership.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-142 failed: schema is not draft-07")
if schema.get("id") != "QUEUE_PUTREQ_EVENT_HANDLE_OWNERSHIP":
    raise SystemExit("SREV-142 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "callsvc.c owns the caller original event handle returned by CreateEvent until it is transferred to out_EventHandle or closed",
    "The allocated QUEUE_PUTREQ_REQ buffer is a wire packet and not the durable owner of the event handle after Dll_Free(req)",
    "No cleanup path may read req->event_handle after Dll_Free(req)",
    "queueserver.cpp owns only the duplicated service-side event handle returned by NtDuplicateObject",
    "The service duplicate must request EVENT_MODIFY_STATE because the service later calls SetEvent on that handle",
    "Failed PutReq calls close any caller-side event handle that was not transferred to the caller",
    "Successful PutReq calls transfer the caller-side event handle only when out_EventHandle is non-null otherwise the local owner closes it",
]:
    require(contracts, term, "schema")

callsvc = (ROOT / "Sandboxie/core/dll/callsvc.c").read_text()
queueserver = (ROOT / "Sandboxie/core/svc/queueserver.cpp").read_text()
queuewire = (ROOT / "Sandboxie/core/svc/queuewire.h").read_text()
pipeserver_h = (ROOT / "Sandboxie/core/svc/PipeServer.h").read_text()
spec = (ROOT / "docs/plan/srev-142-queue-putreq-event-handle-ownership.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-142.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "struct tagQUEUE_PUTREQ_REQ",
    "WCHAR queue_name[QUEUE_NAME_MAXLEN];",
    "__declspec(align(8)) ULONG64 event_handle;",
    "ULONG data_len;",
    "UCHAR data[1];",
    "struct tagQUEUE_PUTREQ_RPL",
    "ULONG req_id;",
]:
    require(queuewire, term, "queue wire shape")

for term in [
    "#define PIPE_MAX_DATA_LEN   0x00FFFFFF",
    "#define LONG_REPLY(ln)  (PipeServer::GetPipeServer()->AllocMsg(ln))",
    "#define SHORT_REPLY(st) (PipeServer::GetPipeServer()->AllocShortMsg(st))",
]:
    require(pipeserver_h, term, "pipe server allocation contract")

func_start = callsvc.index("_FX ULONG SbieDll_QueuePutReqImpl")
func_end = callsvc.index("//---------------------------------------------------------------------------\n// SbieDll_StartProxy", func_start)
putreq = callsvc[func_start:func_end]

for term in [
    "HANDLE EventHandle = NULL;",
    "req_len = sizeof(QUEUE_PUTREQ_REQ) + DataLen;",
    "req = Dll_Alloc(req_len);",
    "req->h.length = req_len;",
    "req->h.msgid  = MSGID_QUEUE_PUTREQ;",
    "req->data_len = DataLen;",
    "EventHandle = CreateEvent(NULL, FALSE, FALSE, NULL);",
    "req->event_handle = (ULONG64)(ULONG_PTR)EventHandle;",
    "if (! EventHandle)",
    "rpl = (QUEUE_PUTREQ_RPL *)SbieDll_CallServer(&req->h);",
    "*out_EventHandle = EventHandle;",
    "EventHandle = NULL;",
    "Dll_Free(req);",
    "if (EventHandle)\n        CloseHandle(EventHandle);",
]:
    require(putreq, term, "client event owner")

final_req_free = putreq.rindex("Dll_Free(req);")
after_free = putreq[final_req_free:]
reject(after_free, "req->event_handle", "post-free request packet")
reject(after_free, "CloseHandle((HANDLE)req->event_handle)", "post-free event close")

if final_req_free > putreq.index("if (EventHandle)\n        CloseHandle(EventHandle);"):
    raise SystemExit("SREV-142 failed: EventHandle close appears before request buffer free")

for term in [
    "MSG_HEADER *QueueServer::PutReqHandler(MSG_HEADER *msg, HANDLE idProcess)",
    "QUEUE_PUTREQ_REQ *req = (QUEUE_PUTREQ_REQ *)msg;",
    "if (req->h.length < sizeof(QUEUE_PUTREQ_REQ))",
    "if ((! req->data_len) || (req->data_len > PIPE_MAX_DATA_LEN))",
    "ULONG offset = FIELD_OFFSET(QUEUE_PUTREQ_REQ, data);",
    "if (offset + req->data_len > req->h.length)",
    "status = OpenProcess(idProcess, &hProcess);",
    "status = DuplicateEvent(hProcess, req->event_handle, &hEvent);",
    "RequestObj->client_event = hEvent;",
    "hEvent = NULL;",
    "List_Insert_After(&QueueObj->requests, NULL, RequestObj);",
    "if (QueueObj->server_event)\n            SetEvent(QueueObj->server_event);",
    "if (hEvent)\n        CloseHandle(hEvent);",
]:
    require(queueserver, term, "service PutReq route")

for term in [
    "LONG QueueServer::DuplicateEvent(",
    "status = NtDuplicateObject(hProcess, (HANDLE)(ULONG_PTR)hEvent,",
    "GetCurrentProcess(), out_hEvent,",
    "EVENT_MODIFY_STATE, 0, 0);",
    "if (status == STATUS_ACCESS_DENIED)\n                status = STATUS_PRIVILEGE_NOT_HELD;",
    "if (RequestObj->client_event)\n        NtClose(RequestObj->client_event);",
    "if (RequestObj->rpl_data_ptr)\n        HeapFree(m_heap, 0, RequestObj->rpl_data_ptr);",
]:
    require(queueserver, term, "service duplicate cleanup")

for term in [
    "Sandboxie/core/svc/queueserver.cpp",
    "Sandboxie/core/dll/callsvc.c",
    "### SREV-142: Queue PutReq Event Handle Ownership",
    "QUEUE_PUTREQ_EVENT_HANDLE_OWNERSHIP",
    "srev-142-queue-putreq-event-handle-ownership.schema.json",
    "EventHandle",
    "EVENT_MODIFY_STATE",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-142 schema/source gate passed")
