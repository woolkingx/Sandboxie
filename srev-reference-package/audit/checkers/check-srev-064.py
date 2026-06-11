#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-064 failed: {label} missing {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-064-rpcrt-string-binding-pointer-gate.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-064 failed: schema is not draft-07")
if schema.get("id") != "RPCRT_STRING_BINDING_POINTER_GATE":
    raise SystemExit("SREV-064 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "pointer to a string binding and an output binding pointer",
    "StringBinding is non-null and not the 0x4 sentinel",
    "OutBinding is non-null",
    "returns RPC_S_INVALID_ARG before local wide-string parsing",
    "spooler dynamic-port rewrite remains behind the same pointer gate",
]:
    require(contracts, term, "schema")

src = (ROOT / "Sandboxie/core/dll/rpcrt.c").read_text()
spec = (ROOT / "docs/plan/srev-064-rpcrt-string-binding-pointer-gate.md").read_text()
ledger = read_combined_ledger(ROOT)

start = src.index("_FX ULONG RpcRt_RpcBindingFromStringBindingW(")
end = src.index("// RpcRt_RpcStringBindingComposeW", start)
func = src[start:end]

gate = "if (!StringBinding || !OutBinding || 0x4 == (ULONG_PTR)StringBinding) {\n        return RPC_S_INVALID_ARG;\n    }"
require(func, gate, "RpcRt_RpcBindingFromStringBindingW source")

for stale in [
    "if(0x4 == (ULONG_PTR)StringBinding)",
    "if (0x4 == (ULONG_PTR)StringBinding)",
]:
    if stale in func:
        raise SystemExit(f"SREV-064 failed: stale sentinel-only gate remains: {stale}")

gate_index = func.index("if (!StringBinding || !OutBinding || 0x4 == (ULONG_PTR)StringBinding)")
for parser in [
    "_wcsicmp(StringBinding",
    "RpcRt_FindModulePreset(CallingModule, StringBinding",
    "wcsstr(StringBinding",
    "__sys_RpcBindingFromStringBindingW(*wstrPortName ? wstrPortName : StringBinding, OutBinding)",
    "*OutBinding",
]:
    parser_index = func.index(parser)
    if parser_index < gate_index:
        raise SystemExit(f"SREV-064 failed: {parser} appears before pointer gate")

for term in [
    "https://learn.microsoft.com/en-us/windows/win32/api/rpcdce/nf-rpcdce-rpcbindingfromstringbindingw",
    "https://learn.microsoft.com/en-us/windows/win32/rpc/rpc-return-values",
    "srev-064-rpcrt-string-binding-pointer-gate.schema.json",
]:
    require(spec, term, "spec")

for term in [
    "### SREV-064: RPCRT String Binding Pointer Gate",
    "RPCRT_STRING_BINDING_POINTER_GATE",
    "srev-064-rpcrt-string-binding-pointer-gate.schema.json",
]:
    require(ledger, term, "ledger")

print("SREV-064 schema/source gate passed")
