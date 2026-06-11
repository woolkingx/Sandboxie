#!/usr/bin/env python3
import json
import re
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-082 failed: {label} missing {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-082-sh-fake-shellapp-queryinterface.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-082 failed: schema is not draft-07")
if schema.get("id") != "SH_FAKE_SHELLAPP_QUERYINTERFACE":
    raise SystemExit("SREV-082 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "IUnknown, IDispatch, IShellDispatch, and IShellDispatch2",
    "increments the object refcount",
    "E_NOINTERFACE",
    "IShellDispatch3/4/5/6 must not be accepted",
    "null ppv returns E_POINTER",
    "supported interface set is static",
]:
    require(contracts, term, "schema")

src = (ROOT / "Sandboxie/core/dll/sh.c").read_text()
spec = (ROOT / "docs/plan/srev-082-sh-fake-shellapp-queryinterface.md").read_text()
ledger = read_combined_ledger(ROOT)

start = src.index("static HRESULT WINAPI SH32_FakeApp_QI(")
end = src.index("static HRESULT WINAPI SH32_FakeApp_get_Application", start)
func = src[start:end]

for term in [
    "if (!ppv) return E_POINTER;",
    "memcmp(riid, &SH32_IID_IUnknown",
    "memcmp(riid, &SH32_IID_IDispatch",
    "memcmp(riid, &SH32_IID_IShellDispatch,",
    "memcmp(riid, &SH32_IID_IShellDispatch2,",
    "*ppv = pThis;",
    "InterlockedIncrement(&pThis->refCount);",
    "return S_OK;",
    "*ppv = NULL;",
    "return E_NOINTERFACE;",
    "SREV-082: do not accept IShellDispatch3/4/5/6 here.",
    "vtable slots beyond this 39-entry IShellDispatch2 table.",
]:
    require(func, term, "SH32_FakeApp_QI")

for bad in [
    "SH32_IID_IShellDispatch3",
    "SH32_IID_IShellDispatch4",
    "SH32_IID_IShellDispatch5",
    "SH32_IID_IShellDispatch6",
]:
    if bad in func:
        raise SystemExit(f"SREV-082 failed: unsupported dispatch IID accepted: {bad}")

if "would be wrong" in func:
    raise SystemExit("SREV-082 failed: stale risk wording remains in FakeShellApp QI")

vtbl_start = src.index("static const ULONG_PTR SH32_FakeApp_Vtbl[] = {")
vtbl_end = src.index("};", vtbl_start)
vtbl = src[vtbl_start:vtbl_end]
slots = [int(match.group(1)) for match in re.finditer(r"// \[(\d+)\]", vtbl)]
if slots != list(range(39)):
    raise SystemExit(f"SREV-082 failed: IShellDispatch2 vtable slots are not 0..38: {slots}")
require(src, "// IShellDispatch2 vtable: 39 entries [0..38]", "vtable comment")
require(vtbl, "SH32_FakeApp_ShellExecute", "vtable ShellExecute slot")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "### SREV-082: Shell FakeApp QueryInterface Vtable Boundary",
    "SH_FAKE_SHELLAPP_QUERYINTERFACE",
    "srev-082-sh-fake-shellapp-queryinterface.schema.json",
]:
    require(ledger, term, "ledger")

print("SREV-082 schema/source gate passed")
