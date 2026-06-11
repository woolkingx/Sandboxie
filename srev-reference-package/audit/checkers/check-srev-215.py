#!/usr/bin/env python3
import json
from pathlib import Path

from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-215 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-215 failed: stale {label} remains {needle!r}")


def between(text: str, start: str, end: str) -> str:
    a = text.index(start)
    b = text.index(end, a + len(start))
    return text[a:b]


schema = json.loads(
    (ROOT / "docs/plan/srev-215-proxyhandle-destructor-drain.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-215 failed: schema is not draft-07")
if schema.get("id") != "PROXYHANDLE_DESTRUCTOR_DRAIN":
    raise SystemExit("SREV-215 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/svc/ProxyHandle.cpp":
    raise SystemExit("SREV-215 failed: wrong owner")
if schema.get("declaration") != "Sandboxie/core/svc/ProxyHandle.h":
    raise SystemExit("SREV-215 failed: wrong declaration")

contracts = "\n".join(schema["contracts"])
for term in [
    "PROXY_HANDLE allocated from m_heap",
    "reachable from m_list",
    "m_close_callback exactly once",
    "HeapFree",
    "destructor drains every remaining list entry",
    "before deleting m_lock",
]:
    require(contracts, term, "schema contract")

spec = (ROOT / "docs/plan/srev-215-proxyhandle-destructor-drain.md").read_text()
source = (ROOT / "Sandboxie/core/svc/ProxyHandle.cpp").read_text()
header = (ROOT / "Sandboxie/core/svc/ProxyHandle.h").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-215.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "ProxyHandle(HANDLE heap, ULONG size_of_data,",
    "~ProxyHandle();",
    "void ReleaseProcess(HANDLE process_id);",
]:
    require(header, term, "header public contract")

destructor = between(
    source,
    "ProxyHandle::~ProxyHandle()",
    "//---------------------------------------------------------------------------\n// Create",
)
for term in [
    "EnterCriticalSection(&m_lock);",
    "PROXY_HANDLE *proxy = (PROXY_HANDLE *)List_Head(&m_list);",
    "PROXY_HANDLE *proxy_next = (PROXY_HANDLE *)List_Next(proxy);",
    "m_close_callback(m_context_for_callback, &proxy->data);",
    "List_Remove(&m_list, proxy);",
    "HeapFree(m_heap, 0, proxy);",
    "proxy = proxy_next;",
    "LeaveCriticalSection(&m_lock);",
    "DeleteCriticalSection(&m_lock);",
]:
    require(destructor, term, "destructor drain")
reject(destructor, "// cleanup CS\n    DeleteCriticalSection(&m_lock);", "destructor-only critical-section cleanup")

close = between(
    source,
    "void ProxyHandle::Close(void *proxy_data)",
    "//---------------------------------------------------------------------------\n// Release",
)
require(close, "proxy->unique_id = 0;", "Close invalidates published id")
require(close, "Release(proxy_data);\n    Release(proxy_data);", "Close releases find and create references")

for name, start, end in [
    ("Release", "void ProxyHandle::Release(void *proxy_data)", "//---------------------------------------------------------------------------\n// ReleaseProcess"),
    ("ReleaseProcess", "void ProxyHandle::ReleaseProcess(HANDLE process_id)", ""),
]:
    if name == "ReleaseProcess":
        section = source[source.index(start):]
    else:
        section = between(source, start, end)
    require(section, "m_close_callback(m_context_for_callback, &proxy->data);", f"{name} callback")
    require(section, "List_Remove(&m_list, proxy);", f"{name} list remove")
    require(section, "HeapFree(m_heap, 0, proxy);", f"{name} heap free")

for term in [
    "kind: srev-ledger-entry",
    "id: SREV-215",
    "owner: Sandboxie/core/svc/ProxyHandle.cpp",
    "declaration: Sandboxie/core/svc/ProxyHandle.h",
    "spec: docs/plan/srev-215-proxyhandle-destructor-drain.md",
    "schema: docs/plan/srev-215-proxyhandle-destructor-drain.schema.json",
    "checker: docs/plan/check-srev-215.py",
    "patched source-level after official heap and critical-section lifetime review",
]:
    require(ledger_fragment, term, "ledger fragment")
    require(ledger, term, "combined ledger")

print("SREV-215 source gate passed")
