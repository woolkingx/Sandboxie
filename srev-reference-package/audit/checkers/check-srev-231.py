#!/usr/bin/env python3
import json
from pathlib import Path

from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-231 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-231 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-231-pstore-server-header-topology.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-231 failed: schema is not draft-07")
if schema.get("id") != "PSTORE_SERVER_HEADER_TOPOLOGY_CONTRACT":
    raise SystemExit("SREV-231 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/svc/pstoreserver.h":
    raise SystemExit("SREV-231 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "PStore broker declaration header",
    "provider pointer slot",
    "does not own PStore COM ABI shape",
    "pstoreserver.cpp, pstorewire.h, ipstore_impl.cpp, ipstore_enum.cpp, or pstore.h",
    "PipeServer route topology and provider-state ownership",
]:
    require(contracts, term, "schema contract")

spec = (ROOT / "docs/plan/srev-231-pstore-server-header-topology.md").read_text()
header = (ROOT / "Sandboxie/core/svc/pstoreserver.h").read_text()
source = (ROOT / "Sandboxie/core/svc/pstoreserver.cpp").read_text()
main = (ROOT / "Sandboxie/core/svc/main.cpp").read_text()
wire = (ROOT / "Sandboxie/core/svc/pstorewire.h").read_text()
ledger = read_combined_ledger(ROOT)
fragment = (ROOT / "docs/plan/ledger/srev-231.md").read_text()

for term in [
    '#include "PipeServer.h"',
    "class PStoreServer",
    "PStoreServer(PipeServer *pipeServer);",
    "static MSG_HEADER *Handler(void *_this, MSG_HEADER *msg);",
    "MSG_HEADER *GetTypeInfo(MSG_HEADER *msg);",
    "MSG_HEADER *GetSubtypeInfo(MSG_HEADER *msg);",
    "MSG_HEADER *ReadItem(MSG_HEADER *msg);",
    "MSG_HEADER *EnumTypes(MSG_HEADER *msg);",
    "MSG_HEADER *EnumItems(MSG_HEADER *msg);",
    "static DWORD connectToPStore(void *__this);",
    "void *m_pStore;",
]:
    require(header, term, "header declaration")

for forbidden in [
    "PStoreCreateInstance",
    "LoadLibrary",
    "QueueUserWorkItem",
    "PipeServer::ImpersonateCaller",
    "CoTaskMemFree",
    "PSTORE_GET_TYPE_INFO_REQ",
]:
    reject(header, forbidden, "runtime owner code in header")

for term in [
    "PStoreServer::PStoreServer(PipeServer *pipeServer)",
    "pipeServer->Register(MSGID_PSTORE, this, Handler);",
    "QueueUserWorkItem(connectToPStore, this, WT_EXECUTELONGFUNCTION);",
    "DWORD PStoreServer::connectToPStore(void *__this)",
    "InterlockedExchangePointer(&_this->m_pStore, pStore);",
    "MSG_HEADER *PStoreServer::Handler(void *_this, MSG_HEADER *msg)",
    "PipeServer::ImpersonateCaller(&msg)",
    "MSGID_PSTORE_GET_TYPE_INFO",
    "MSGID_PSTORE_GET_SUBTYPE_INFO",
    "MSGID_PSTORE_READ_ITEM",
    "MSGID_PSTORE_ENUM_TYPES",
    "MSGID_PSTORE_ENUM_ITEMS",
]:
    require(source, term, "source dispatch topology")

require(main, "new PStoreServer(pipeServer);", "main startup topology")
for term in [
    "PSTORE_GET_TYPE_INFO_REQ",
    "PSTORE_GET_SUBTYPE_INFO_REQ",
    "PSTORE_READ_ITEM_REQ",
    "PSTORE_ENUM_TYPES_REQ",
    "PSTORE_ENUM_ITEMS_REQ",
]:
    require(wire, term, "wire owner topology")

for term in [
    "SREV-161 already owns the service-side PStore enumeration",
    "SREV-206 owns the DLL hook output contract",
    "SREV-226 owns the local PStore enumerator",
    "No source patch",
    "local service-topology classification",
    "absence of runtime owner claims",
]:
    require(spec, term, "spec classification")

for term in [
    "### SREV-161: PStore Enumerator End Contract",
    "owner: Sandboxie/core/svc/pstoreserver.cpp",
    "### SREV-206: PStoreCreateInstance Output Contract",
    "owner: Sandboxie/core/dll/pst.cpp",
    "### SREV-226: PStore Enumerator QueryInterface Contract",
    "owner: Sandboxie/core/dll/ipstore_enum.cpp",
]:
    require(ledger, term, "existing PStore owner coverage")

for term in [
    "kind: srev-ledger-entry",
    "id: SREV-231",
    "owner: Sandboxie/core/svc/pstoreserver.h",
    "docs-only-source-topology-reviewed",
    "srev-231-pstore-server-header-topology.schema.json",
    "check-srev-231.py",
]:
    require(fragment, term, "ledger fragment")
    require(ledger, term, "combined ledger")

print("SREV-231 source gate passed")
