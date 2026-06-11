#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-207 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-207 failed: stale {label} remains {needle!r}")


def between(text: str, start: str, end: str) -> str:
    a = text.index(start)
    b = text.index(end, a + len(start))
    return text[a:b]


schema = json.loads(
    (ROOT / "docs/plan/srev-207-queue-name-wire-copy-contract.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-207 failed: schema is not draft-07")
if schema.get("id") != "QUEUE_NAME_WIRE_COPY_CONTRACT":
    raise SystemExit("SREV-207 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/svc/queueserver.h":
    raise SystemExit("SREV-207 failed: wrong owner")
if schema.get("implementation") != "Sandboxie/core/dll/callsvc.c":
    raise SystemExit("SREV-207 failed: wrong implementation")
if schema.get("wire_schema") != "Sandboxie/core/svc/queuewire.h":
    raise SystemExit("SREV-207 failed: wrong wire schema")

contracts = "\n".join(schema["contracts"])
for term in [
    "QueueServer declaration boundary",
    "QUEUE_NAME_MAXLEN WCHARs",
    "bounded helper before sending a queue wire packet",
    "STATUS_INVALID_PARAMETER",
    "checked after Dll_Alloc before writing header or queue-name fields",
    "MakeQueueName still owns sandbox path prefixing",
]:
    require(contracts, term, "schema contract")

queueserver_h = (ROOT / "Sandboxie/core/svc/queueserver.h").read_text()
queueserver_cpp = (ROOT / "Sandboxie/core/svc/queueserver.cpp").read_text()
queuewire = (ROOT / "Sandboxie/core/svc/queuewire.h").read_text()
callsvc = (ROOT / "Sandboxie/core/dll/callsvc.c").read_text()
spec = (ROOT / "docs/plan/srev-207-queue-name-wire-copy-contract.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-207.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "class QueueServer",
    "WCHAR *MakeQueueName(",
    "void *FindQueueObj(const WCHAR *QueueName);",
]:
    require(queueserver_h, term, "QueueServer owner declaration")

for term in [
    "#define QUEUE_NAME_MAXLEN   64",
    "WCHAR queue_name[QUEUE_NAME_MAXLEN];",
    "struct tagQUEUE_CREATE_REQ",
    "struct tagQUEUE_GETREQ_REQ",
    "struct tagQUEUE_PUTRPL_REQ",
    "struct tagQUEUE_PUTREQ_REQ",
    "struct tagQUEUE_GETRPL_REQ",
]:
    require(queuewire, term, "fixed queue wire shape")

for term in [
    "static BOOLEAN SbieDll_QueueCopyName(WCHAR *dst, const WCHAR *QueueName)",
    "if (! QueueName)",
    "for (i = 0; i < QUEUE_NAME_MAXLEN; ++i)",
    "dst[i] = QueueName[i];",
    "if (QueueName[i] == L'\\0')",
    "dst[QUEUE_NAME_MAXLEN - 1] = L'\\0';",
    "return FALSE;",
]:
    require(callsvc, term, "bounded copy helper")

for term in [
    "SbieDll_QueueCreate",
    "SbieDll_QueueGetReq",
    "SbieDll_QueuePutRpl",
    "SbieDll_QueuePutReqImpl",
    "SbieDll_StartProxy",
    "SbieDll_QueueGetRpl",
]:
    fn = between(callsvc, f"_FX ULONG {term}", "//---------------------------------------------------------------------------")
    require(fn, "SbieDll_QueueCopyName", f"{term} bounded copy")
    reject(fn, "wcscpy(", f"{term} direct wcscpy")

for term in [
    "req = Dll_Alloc(req_len);\n    if (! req)\n        return STATUS_INSUFFICIENT_RESOURCES;",
    "if (! SbieDll_QueueCopyName(req->queue_name, QueueName)) {\n        Dll_Free(req);\n        return STATUS_INVALID_PARAMETER;\n    }",
]:
    require(callsvc, term, "heap request packet gate")

for term in [
    "WCHAR *QueueServer::MakeQueueName(",
    "req_name[QUEUE_NAME_MAXLEN - 1] = L'\\0';",
    "if (req_name[0] == L'*')",
    "SbieApi_QueryProcessPath(",
    "void *QueueServer::FindQueueObj(const WCHAR *QueueName)",
]:
    require(queueserver_cpp, term, "server name owner boundary")

for term in [
    "kind: srev-ledger-entry",
    "id: SREV-207",
    "owner: Sandboxie/core/svc/queueserver.h",
    "implementation: Sandboxie/core/dll/callsvc.c",
    "wire_schema: Sandboxie/core/svc/queuewire.h",
    "spec: docs/plan/srev-207-queue-name-wire-copy-contract.md",
    "schema: docs/plan/srev-207-queue-name-wire-copy-contract.schema.json",
    "checker: docs/plan/check-srev-207.py",
    "patched source-level after official bounded string copy shape review",
]:
    require(ledger_fragment, term, "ledger fragment")
    require(ledger, term, "combined ledger")

print("SREV-207 source gate passed")
