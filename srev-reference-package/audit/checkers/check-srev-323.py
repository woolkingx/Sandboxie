#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-323 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-323 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-323-rpcrt-binding-string-sentinel-gate.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-323 failed: schema is not draft-07")
if schema.get("id") != "RPCRT_BINDING_STRING_SENTINEL_GATE":
    raise SystemExit("SREV-323 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/dll/rpcrt.c":
    raise SystemExit("SREV-323 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "official RpcBindingFromStringBinding owns valid string-binding parsing",
    "pre-forward local pointer and sentinel rejection",
    "observed 0x4 sentinel return RPC_S_INVALID_ARG",
    "local sentinel, not an official string-binding shape",
    "changes comments and proof only",
]:
    require(contracts, term, "schema contracts")

rpcrt = (ROOT / "Sandboxie/core/dll/rpcrt.c").read_text()
spec = (ROOT / "docs/plan/srev-323-rpcrt-binding-string-sentinel-gate.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-323.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

start = rpcrt.index("_FX ULONG RpcRt_RpcBindingFromStringBindingW(")
end = rpcrt.index("// RpcRt_RpcBindingCreateA", start)
binding_func = rpcrt[start:end]

for term in [
    "SREV-323: reject the observed 0x4 binding-string sentinel locally.",
    "Official RpcBindingFromStringBinding owns valid string-binding errors.",
    "if (!StringBinding || !OutBinding || 0x4 == (ULONG_PTR)StringBinding) {\n        return RPC_S_INVALID_ARG;\n    }",
    "if (_wcsicmp(StringBinding, dynamicFalse) == 0)",
    "status = __sys_RpcBindingFromStringBindingW(*wstrPortName ? wstrPortName : StringBinding, OutBinding);",
]:
    require(binding_func, term, "RpcBindingFromStringBindingW source")

guard = binding_func.index("if (!StringBinding || !OutBinding || 0x4 == (ULONG_PTR)StringBinding)")
compare = binding_func.index("if (_wcsicmp(StringBinding, dynamicFalse) == 0)")
native = binding_func.index("status = __sys_RpcBindingFromStringBindingW")
if not guard < compare < native:
    raise SystemExit("SREV-323 failed: sentinel guard must precede local compare and native call")

for stale in [
    "will result in a crash",
    "StringBinging",
    "Microsoft adds 0x4",
]:
    reject(binding_func, stale, "RpcBindingFromStringBindingW sentinel comment")

for term in [
    "RPCRT_BINDING_STRING_SENTINEL_GATE",
    "observed `0x4` binding-string sentinel",
    "The sentinel gate is deliberately before any `_wcsicmp`",
    "No null/sentinel predicate, return code, binding rewrite",
]:
    require(spec, term, "spec")

for term in [
    "kind: srev-ledger-entry",
    "id: SREV-323",
    "owner: Sandboxie/core/dll/rpcrt.c",
    "spec: docs/plan/srev-323-rpcrt-binding-string-sentinel-gate.md",
    "schema: docs/plan/srev-323-rpcrt-binding-string-sentinel-gate.schema.json",
    "checker: docs/plan/check-srev-323.py",
]:
    require(ledger_fragment, term, "ledger fragment header")

for term in [
    "### SREV-323: RPCRT Binding String Sentinel Gate",
    "RPCRT_BINDING_STRING_SENTINEL_GATE",
    "RpcBindingFromStringBinding",
    "RPC_S_INVALID_ARG",
]:
    require(ledger, term, "combined ledger")

print("SREV-323 schema/source gate passed")
