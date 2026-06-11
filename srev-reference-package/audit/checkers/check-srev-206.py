#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-206 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-206 failed: stale {label} remains {needle!r}")


def between(text: str, start: str, end: str) -> str:
    a = text.index(start)
    b = text.index(end, a + len(start))
    return text[a:b]


schema = json.loads(
    (ROOT / "docs/plan/srev-206-pstore-create-instance-output-contract.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-206 failed: schema is not draft-07")
if schema.get("id") != "PSTORE_CREATE_INSTANCE_OUTPUT_CONTRACT":
    raise SystemExit("SREV-206 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/dll/pst.cpp":
    raise SystemExit("SREV-206 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "local Protected Storage hook boundary",
    "ppProvider is an out pointer",
    "output slot is cleared before returning failure",
    "GetProcAddress may only be called after the GetModuleHandle result is proven non-NULL",
    "Success publishes a local IPStoreImpl",
    "pReserved and dwFlags semantic fidelity remains a Windows runtime compatibility gate",
]:
    require(contracts, term, "schema contract")

src = (ROOT / "Sandboxie/core/dll/pst.cpp").read_text()
spec = (ROOT / "docs/plan/srev-206-pstore-create-instance-output-contract.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-206.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

fn = between(
    src,
    "_FX HRESULT Pst_PStoreCreateInstance(",
    "//---------------------------------------------------------------------------\n// Pst_Init",
)

for term in [
    "if (! ppProvider)\n        return E_POINTER;",
    "*ppProvider = NULL;",
    "HMODULE ole32 = GetModuleHandle(DllName_ole32_or_combase);",
    "if (! ole32)\n            return E_FAIL;",
    "__sys_CoTaskMemAlloc = GetProcAddress(ole32, \"CoTaskMemAlloc\");",
    "if (! __sys_CoTaskMemAlloc)\n            return E_FAIL;",
    "*ppProvider = new IPStoreImpl(__sys_CoTaskMemAlloc);",
    "return S_OK;",
]:
    require(fn, term, "PStoreCreateInstance gate")

if not fn.index("if (! ppProvider)") < fn.index("*ppProvider = NULL;"):
    raise SystemExit("SREV-206 failed: output slot cleared before ppProvider gate")
if not fn.index("*ppProvider = NULL;") < fn.index("if (! __sys_CoTaskMemAlloc)"):
    raise SystemExit("SREV-206 failed: output slot not cleared before allocator lookup")
if not fn.index("HMODULE ole32 = GetModuleHandle") < fn.index("if (! ole32)"):
    raise SystemExit("SREV-206 failed: module handle check is before module lookup")
if not fn.index("if (! ole32)") < fn.index("GetProcAddress(ole32, \"CoTaskMemAlloc\")"):
    raise SystemExit("SREV-206 failed: GetProcAddress can run before module handle check")
if not fn.index("if (! __sys_CoTaskMemAlloc)") < fn.index("*ppProvider = new IPStoreImpl"):
    raise SystemExit("SREV-206 failed: provider can be published before allocator gate")

reject(fn, "HMODULE ole32 = GetModuleHandle(DllName_ole32_or_combase);\n        __sys_CoTaskMemAlloc = GetProcAddress", "unchecked module handle lookup")

for term in [
    "kind: srev-ledger-entry",
    "id: SREV-206",
    "owner: Sandboxie/core/dll/pst.cpp",
    "spec: docs/plan/srev-206-pstore-create-instance-output-contract.md",
    "schema: docs/plan/srev-206-pstore-create-instance-output-contract.schema.json",
    "checker: docs/plan/check-srev-206.py",
    "patched source-level after official PStore output/loader shape review",
]:
    require(ledger_fragment, term, "ledger fragment")
    require(ledger, term, "combined ledger")

print("SREV-206 source gate passed")
