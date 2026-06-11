#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-343 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-343 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-343-util-registry-existence-dummy-buffer.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-343 failed: schema is not draft-07")
if schema.get("id") != "UTIL_REGISTRY_EXISTENCE_DUMMY_BUFFER":
    raise SystemExit("SREV-343 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/drv/util.c":
    raise SystemExit("SREV-343 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "caller-provided storage",
    "initialized UNICODE_STRING",
    "NULL UNICODE_STRING Buffer lets RtlQueryRegistryValues allocate",
    "dummy one-WCHAR buffer prevents API allocation",
    "RTL_QUERY_REGISTRY_DIRECT and RTL_QUERY_REGISTRY_TYPECHECK",
    "STATUS_SUCCESS STATUS_OBJECT_TYPE_MISMATCH and STATUS_BUFFER_TOO_SMALL",
    "This SREV changes comments and proof only",
]:
    require(contracts, term, "schema")

util = (ROOT / "Sandboxie/core/drv/util.c").read_text()
spec = (ROOT / "docs/plan/srev-343-util-registry-existence-dummy-buffer.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-343.md").read_text()

exist_start = util.index("BOOLEAN DoesRegValueExist(")
exist_end = util.index("NTSTATUS GetRegString(", exist_start)
exist_block = util[exist_start:exist_end]

get_start = util.index("NTSTATUS GetRegString(")
get_end = util.index("_FX ULONG GetRegDword(", get_start)
get_block = util[get_start:get_end]

for term in [
    "SREV-343: RTL_QUERY_REGISTRY_DIRECT stores REG_SZ data through an",
    "initialized UNICODE_STRING",
    "NULL Buffer lets the API allocate",
    "caller-owned one-WCHAR storage",
    "WCHAR DummyBuffer[1] = {0};",
    "UNICODE_STRING Dummy = { 0, sizeof(DummyBuffer), DummyBuffer };",
    "GetRegString(RelativeTo, Path, ValueName, &Dummy);",
    "status == STATUS_SUCCESS || status == STATUS_OBJECT_TYPE_MISMATCH || status == STATUS_BUFFER_TOO_SMALL",
]:
    require(exist_block, term, "DoesRegValueExist")

reject(exist_block, "memory pool leak somewhere in the kernel", "DummyBuffer comment")
reject(exist_block, "NULL buffer, this will cause", "DummyBuffer comment")

for term in [
    "RTL_QUERY_REGISTRY_REQUIRED",
    "RTL_QUERY_REGISTRY_DIRECT",
    "RTL_QUERY_REGISTRY_TYPECHECK",
    "RTL_QUERY_REGISTRY_NOVALUE",
    "RTL_QUERY_REGISTRY_NOEXPAND",
    "qrt[0].EntryContext = pData;",
    "qrt[0].DefaultType = (REG_SZ << RTL_QUERY_REGISTRY_TYPECHECK_SHIFT) | REG_NONE;",
    "RtlQueryRegistryValues(",
]:
    require(get_block, term, "GetRegString")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "If `UNICODE_STRING.Buffer` is `NULL`, the routine allocates",
    "RTL_QUERY_REGISTRY_TYPECHECK",
    "Windows can bug",
    "check when direct registry queries omit type checking",
    "Runtime gate:",
]:
    require(spec, term, "spec official shape")

for term in [
    "### SREV-343: Util Registry Existence Dummy Buffer",
    "UTIL_REGISTRY_EXISTENCE_DUMMY_BUFFER",
    "srev-343-util-registry-existence-dummy-buffer.schema.json",
    "Sandboxie/core/drv/util.c",
    "DoesRegValueExist",
    "GetRegString",
    "RTL_QUERY_REGISTRY_DIRECT",
    "DummyBuffer",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-343 source gate passed")
