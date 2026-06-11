#!/usr/bin/env python3
import json
import re
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-189 failed: {label} missing {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-189-core-heapfree-flag-contract.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-189 failed: schema is not draft-07")
if schema.get("id") != "CORE_HEAPFREE_FLAG_CONTRACT":
    raise SystemExit("SREV-189 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core":
    raise SystemExit("SREV-189 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "HeapFree owns release",
    "dwFlags uses the heap-free option schema",
    "HEAP_GENERATE_EXCEPTIONS is an allocation option",
    "HEAP_NO_SERIALIZE remains disallowed",
    "all HeapFree calls under Sandboxie/core",
    "changes only the HeapFree flag argument",
    "runtime proof is required",
]:
    require(contracts, term, "schema contracts")

spec = (ROOT / "docs/plan/srev-189-core-heapfree-flag-contract.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-189.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for file_name in schema["files"]:
    path = ROOT / file_name
    if not path.exists():
        raise SystemExit(f"SREV-189 failed: file missing {file_name}")
    text = path.read_text(errors="ignore")
    bad = re.findall(r"HeapFree\s*\([^\n;]*HEAP_GENERATE_EXCEPTIONS", text)
    if bad:
        raise SystemExit(f"SREV-189 failed: HeapFree still uses HEAP_GENERATE_EXCEPTIONS in {file_name}")
    require(spec, file_name, "spec file list")
    require(ledger, file_name, "combined ledger file list")

core_bad = []
for path in (ROOT / "Sandboxie/core").rglob("*"):
    if not path.is_file():
        continue
    if path.suffix.lower() not in {".c", ".cpp", ".h"}:
        continue
    text = path.read_text(errors="ignore")
    if re.search(r"HeapFree\s*\([^\n;]*HEAP_GENERATE_EXCEPTIONS", text):
        core_bad.append(str(path.relative_to(ROOT)))
if core_bad:
    raise SystemExit("SREV-189 failed: core HeapFree bad flags remain: " + ", ".join(core_bad))

for term in [
    "HeapFree(GetProcessHeap(), 0, buf);",
    "HeapFree(heap, 0, item->value);",
]:
    require((ROOT / "Sandboxie/core/svc/serviceserver.cpp").read_text()
            + "\n"
            + (ROOT / "Sandboxie/core/dll/ipstore_impl.cpp").read_text(errors="ignore"),
            term,
            "source readback",
    )

for term in [
    "kind: srev-ledger-entry",
    "id: SREV-189",
    "owner: Sandboxie/core",
    "spec: docs/plan/srev-189-core-heapfree-flag-contract.md",
    "schema: docs/plan/srev-189-core-heapfree-flag-contract.schema.json",
    "checker: docs/plan/check-srev-189.py",
]:
    require(ledger_fragment, term, "ledger fragment header")

for term in [
    "### SREV-189: Core HeapFree Flag Contract",
    "CORE_HEAPFREE_FLAG_CONTRACT",
    "HEAP_GENERATE_EXCEPTIONS",
    "HeapFree",
]:
    require(ledger, term, "combined ledger")

print("SREV-189 schema/source gate passed")
