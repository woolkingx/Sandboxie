#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-191 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-191 failed: {label} still contains {needle!r}")


def between(text: str, start: str, end: str) -> str:
    a = text.index(start)
    b = text.index(end, a + len(start))
    return text[a:b]


schema = json.loads(
    (ROOT / "docs/plan/srev-191-namedpipe-pending-io-lifetime-contract.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-191 failed: schema is not draft-07")
if schema.get("id") != "NAMEDPIPE_PENDING_IO_LIFETIME_CONTRACT":
    raise SystemExit("SREV-191 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/svc/namedpipeserver.cpp":
    raise SystemExit("SREV-191 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "pending NtReadFile and NtWriteFile lifetime",
    "IO_STATUS_BLOCK passed to NtReadFile or NtWriteFile must remain valid",
    "transfer buffer passed to NtReadFile or NtWriteFile must remain valid",
    "STATUS_PENDING requires waiting for I/O completion",
    "CancelIo requests cancellation but does not prove",
    "wait for completion after requesting cancellation",
    "event must be reset before each native I/O issue",
    "Only one native read write or set operation may use",
    "per-handle I/O lock is owned by PROXY_PIPE lifetime",
    "LPC and ALPC proxy handles do not own",
]:
    require(contracts, term, "schema contracts")

svc = (ROOT / "Sandboxie/core/svc/namedpipeserver.cpp").read_text()
spec = (ROOT / "docs/plan/srev-191-namedpipe-pending-io-lifetime-contract.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-191.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "CRITICAL_SECTION *pIoLock;",
    "static ULONG NamedPipeServer_WaitForPendingIo(",
    "CancelIo(ProxyPipe->hPipe);",
    "WaitForSingleObject(ProxyPipe->hEvent, INFINITE);",
    "IoStatusBlock->Status = STATUS_CANCELLED;",
    "IoStatusBlock->Information = 0;",
    "return STATUS_CANCELLED;",
]:
    require(svc, term, "pending I/O helper")

open_handler = between(
    svc,
    "MSG_HEADER *NamedPipeServer::OpenHandler(",
    "//---------------------------------------------------------------------------\n// CloseHandler",
)
for term in [
    "ProxyPipe.pIoLock = NULL;",
    "ProxyPipe.hEvent = CreateEvent(NULL, FALSE, FALSE, NULL);",
    "ProxyPipe.pIoLock = (CRITICAL_SECTION *)HeapAlloc(",
    "InitializeCriticalSectionAndSpinCount(",
    "ProxyPipe.pIoLock, 1000)) {",
    "m_ProxyHandle->Create(",
    "idProcess, &ProxyPipe);",
]:
    require(open_handler, term, "OpenHandler lock publication")

lpc_connect = between(
    svc,
    "MSG_HEADER *NamedPipeServer::LpcConnectHandler(",
    "//---------------------------------------------------------------------------\n// LpcRequestHandler",
)
require(lpc_connect, "ProxyPipe.pIoLock = NULL;", "LPC handle non-owner lock state")

close_callback = between(
    svc,
    "void NamedPipeServer::CloseCallback(",
    "//---------------------------------------------------------------------------\n// Handler",
)
for term in [
    "if (ProxyPipe->pIoLock) {",
    "DeleteCriticalSection(ProxyPipe->pIoLock);",
    "HeapFree(GetProcessHeap(), 0, ProxyPipe->pIoLock);",
    "NtClose(ProxyPipe->hEvent);",
    "NtClose(ProxyPipe->hPipe);",
]:
    require(close_callback, term, "CloseCallback lifetime cleanup")

set_handler = between(
    svc,
    "MSG_HEADER *NamedPipeServer::SetHandler(",
    "//---------------------------------------------------------------------------\n// ReadHandler",
)
for term in [
    "if (! ProxyPipe->pIoLock) {",
    "m_ProxyHandle->Release(ProxyPipe);",
    "EnterCriticalSection(ProxyPipe->pIoLock);",
    "NtSetInformationFile(",
    "LeaveCriticalSection(ProxyPipe->pIoLock);",
]:
    require(set_handler, term, "SetHandler serialization")

read_handler = between(
    svc,
    "MSG_HEADER *NamedPipeServer::ReadHandler(",
    "//---------------------------------------------------------------------------\n// WriteHandler",
)
for term in [
    "if (! ProxyPipe->pIoLock) {",
    "m_ProxyHandle->Release(ProxyPipe);",
    "EnterCriticalSection(ProxyPipe->pIoLock);",
    "ResetEvent(ProxyPipe->hEvent);",
    "rpl->h.status = NtReadFile(",
    "rpl->h.status = NamedPipeServer_WaitForPendingIo(",
    "LeaveCriticalSection(ProxyPipe->pIoLock);",
]:
    require(read_handler, term, "ReadHandler pending lifetime")
reject(read_handler, "CancelIo(ProxyPipe->hPipe);\n                rpl->h.status = STATUS_CANCELLED;", "stale read timeout path")
if not (
    read_handler.index("EnterCriticalSection(ProxyPipe->pIoLock);")
    < read_handler.index("ResetEvent(ProxyPipe->hEvent);")
    < read_handler.index("NtReadFile(")
    < read_handler.index("NamedPipeServer_WaitForPendingIo(")
    < read_handler.index("LeaveCriticalSection(ProxyPipe->pIoLock);")
    < read_handler.rindex("m_ProxyHandle->Release(ProxyPipe);")
):
    raise SystemExit("SREV-191 failed: ReadHandler lock/order is wrong")

write_handler = between(
    svc,
    "MSG_HEADER *NamedPipeServer::WriteHandler(",
    "//---------------------------------------------------------------------------\n// LpcConnectHandler",
)
for term in [
    "memzero(&IoStatusBlock, sizeof(IoStatusBlock));",
    "if (! ProxyPipe->pIoLock) {",
    "m_ProxyHandle->Release(ProxyPipe);",
    "EnterCriticalSection(ProxyPipe->pIoLock);",
    "ResetEvent(ProxyPipe->hEvent);",
    "rpl->h.status = NtWriteFile(",
    "if (rpl->h.status != STATUS_PENDING)",
    "IoStatusBlock.Status = rpl->h.status;",
    "rpl->h.status = NamedPipeServer_WaitForPendingIo(",
    "LeaveCriticalSection(ProxyPipe->pIoLock);",
]:
    require(write_handler, term, "WriteHandler pending lifetime")
reject(write_handler, "CancelIo(ProxyPipe->hPipe);\n                rpl->h.status = STATUS_CANCELLED;", "stale write timeout path")
if not (
    write_handler.index("EnterCriticalSection(ProxyPipe->pIoLock);")
    < write_handler.index("ResetEvent(ProxyPipe->hEvent);")
    < write_handler.index("NtWriteFile(")
    < write_handler.index("NamedPipeServer_WaitForPendingIo(")
    < write_handler.index("LeaveCriticalSection(ProxyPipe->pIoLock);")
    < write_handler.rindex("m_ProxyHandle->Release(ProxyPipe);")
):
    raise SystemExit("SREV-191 failed: WriteHandler lock/order is wrong")

for term in [
    "kind: srev-ledger-entry",
    "id: SREV-191",
    "owner: Sandboxie/core/svc/namedpipeserver.cpp",
    "spec: docs/plan/srev-191-namedpipe-pending-io-lifetime-contract.md",
    "schema: docs/plan/srev-191-namedpipe-pending-io-lifetime-contract.schema.json",
    "checker: docs/plan/check-srev-191.py",
]:
    require(ledger_fragment, term, "ledger fragment header")

for term in [
    "### SREV-191: Named Pipe Pending I/O Lifetime Contract",
    "NAMEDPIPE_PENDING_IO_LIFETIME_CONTRACT",
    "Sandboxie/core/svc/namedpipeserver.cpp",
    "CancelIo",
    "IO_STATUS_BLOCK",
    "per-handle I/O lock",
]:
    require(ledger, term, "combined ledger")

print("SREV-191 schema/source gate passed")
