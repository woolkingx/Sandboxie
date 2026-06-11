#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-152 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-152 failed: {label} still contains {needle!r}")


def between(text: str, start: str, end: str) -> str:
    a = text.index(start)
    b = text.index(end, a + len(start))
    return text[a:b]


schema = json.loads(
    (ROOT / "docs/plan/srev-152-pstore-timestamp-map-view-lifetime.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-152 failed: schema is not draft-07")
if schema.get("id") != "PSTORE_TIMESTAMP_MAP_VIEW_LIFETIME":
    raise SystemExit("SREV-152 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "section is a file mapping object handle, not a mapped address",
    "global_timestamp is a mapped view address returned by MapViewOfFile",
    "MapViewOfFile may fail and return NULL; the timestamp pointer is legal to dereference only after a non-null check",
    "A successful mapped view must be unmapped with UnmapViewOfFile before or during owner destruction",
    "Closing the file mapping handle does not replace unmapping the view",
]:
    require(contracts, term, "schema")

impl = (ROOT / "Sandboxie/core/dll/ipstore_impl.cpp").read_text()
header = (ROOT / "Sandboxie/core/dll/ipstore_impl.h").read_text()
spec = (ROOT / "docs/plan/srev-152-pstore-timestamp-map-view-lifetime.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-152.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "HANDLE section;",
    "__int64 *global_timestamp;",
    "IPStoreImpl(void *ptrCoTaskMemAlloc);",
    "~IPStoreImpl();",
]:
    require(header, term, "ipstore_impl.h")

ctor = between(
    impl,
    "IPStoreImpl::IPStoreImpl(void *ptrCoTaskMemAlloc)",
    "IPStoreImpl::~IPStoreImpl()",
)
for term in [
    "global_timestamp = NULL;",
    "section = OpenFileMapping(FILE_MAP_ALL_ACCESS, FALSE, _SectionName);",
    "section = CreateFileMapping(",
    "MapViewOfFile(section, FILE_MAP_ALL_ACCESS, 0, 0, 8);",
    "if (global_timestamp && section_created)",
    "*global_timestamp = local_timestamp + 1;",
]:
    require(ctor, term, "constructor")
reject(ctor, "if (section_created)\n            *global_timestamp", "unguarded initial timestamp write")
if not (
    ctor.index("MapViewOfFile(section, FILE_MAP_ALL_ACCESS, 0, 0, 8);")
    < ctor.index("if (global_timestamp && section_created)")
    < ctor.index("*global_timestamp = local_timestamp + 1;")
):
    raise SystemExit("SREV-152 failed: constructor map-view gate/order is wrong")

dtor = between(
    impl,
    "IPStoreImpl::~IPStoreImpl()",
    "void *IPStoreImpl::operator new",
)
for term in [
    "if (global_timestamp)",
    "UnmapViewOfFile(global_timestamp);",
    "if (section)",
    "CloseHandle(section);",
]:
    require(dtor, term, "destructor")
if not (
    dtor.index("if (global_timestamp)")
    < dtor.index("UnmapViewOfFile(global_timestamp);")
    < dtor.index("if (section)")
    < dtor.index("CloseHandle(section);")
):
    raise SystemExit("SREV-152 failed: destructor unmap-before-close order is wrong")

for term in [
    "if (! global_timestamp)",
    "local_timestamp != *global_timestamp",
    "*global_timestamp = local_timestamp + 1",
]:
    require(impl, term, "timestamp topology")

for term in [
    "Sandboxie/core/dll/ipstore_impl.cpp",
    "Sandboxie/core/dll/ipstore_impl.h",
    "### SREV-152: PStore Timestamp Map View Lifetime",
    "PSTORE_TIMESTAMP_MAP_VIEW_LIFETIME",
    "srev-152-pstore-timestamp-map-view-lifetime.schema.json",
    "CreateFileMapping",
    "MapViewOfFile",
    "UnmapViewOfFile",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-152 schema/source gate passed")
