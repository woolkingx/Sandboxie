#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-079 failed: {label} missing {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-079-registry-existence-buffer-status.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-079 failed: schema is not draft-07")
if schema.get("id") != "REGISTRY_EXISTENCE_BUFFER_STATUS":
    raise SystemExit("SREV-079 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "initialized non-NULL UNICODE_STRING buffer",
    "STATUS_SUCCESS means the value exists",
    "STATUS_OBJECT_TYPE_MISMATCH means the value exists",
    "STATUS_BUFFER_TOO_SMALL means the value exists",
    "missing-key and other failure statuses remain false",
]:
    require(contracts, term, "schema")

src = (ROOT / "Sandboxie/core/drv/util.c").read_text()
spec = (ROOT / "docs/plan/srev-079-registry-existence-buffer-status.md").read_text()
ledger = read_combined_ledger(ROOT)

start = src.index("BOOLEAN DoesRegValueExist(")
end = src.index("NTSTATUS GetRegString", start)
func = src[start:end]

for term in [
    "WCHAR DummyBuffer[1] = {0};",
    "UNICODE_STRING Dummy = { 0, sizeof(DummyBuffer), DummyBuffer };",
    "NTSTATUS status = GetRegString(RelativeTo, Path, ValueName, &Dummy);",
    "return (status == STATUS_SUCCESS || status == STATUS_OBJECT_TYPE_MISMATCH || status == STATUS_BUFFER_TOO_SMALL);",
]:
    require(func, term, "DoesRegValueExist source")

if "NULL" in func.split("NTSTATUS status = GetRegString", 1)[1].split(");", 1)[0]:
    raise SystemExit("SREV-079 failed: GetRegString probe appears to use NULL buffer")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "### SREV-079: Registry Existence Buffer Status",
    "REGISTRY_EXISTENCE_BUFFER_STATUS",
    "srev-079-registry-existence-buffer-status.schema.json",
]:
    require(ledger, term, "ledger")

print("SREV-079 schema/source gate passed")
