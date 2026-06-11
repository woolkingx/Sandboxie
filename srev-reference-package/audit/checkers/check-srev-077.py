#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-077 failed: {label} missing {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-077-format-message-insert-gate.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-077 failed: schema is not draft-07")
if schema.get("id") != "FORMAT_MESSAGE_INSERT_ARRAY_GATE":
    raise SystemExit("SREV-077 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "second FormatMessage pass may run only when an insert array exists",
    "NULL insert array has no legal owner",
    "markers inside insert strings are rejected",
    "successful replacement transfers output ownership",
    "failed replacement preserves the original formatted output",
]:
    require(contracts, term, "schema")

src = (ROOT / "Sandboxie/core/dll/support.c").read_text()
spec = (ROOT / "docs/plan/srev-077-format-message-insert-gate.md").read_text()
ledger = read_combined_ledger(ROOT)

start = src.index("_FX ULONG SbieDll_FormatMessage_2")
end = src.index("// SbieDll_FormatMessage", start)
func = src[start:end]

for term in [
    "SREV-077: for right-to-left language text files",
    "compatibility pass accepts .N. markers",
    "only when an insert array exists",
    "const ULONG FormatFlags     = FORMAT_MESSAGE_FROM_STRING |",
    "FORMAT_MESSAGE_ARGUMENT_ARRAY |",
    "FORMAT_MESSAGE_ALLOCATE_BUFFER;",
    "if (! ins)\n        return 0;",
    "if (ins[1] && wcsstr(ins[1], _x2))\n        return 0;",
    "if (ins[2] && wcsstr(ins[2], _x2))\n        return 0;",
    "rc = FormatMessage(FormatFlags, newtxt, 0, 0,",
    "(LPWSTR)&ptr, 4, (va_list *)ins);",
    "*text_ptr = ptr;\n        LocalFree(oldtxt);",
    "LocalFree(newtxt);\n    return rc;",
]:
    require(func, term, "SbieDll_FormatMessage_2 source")

for stale in [
    "as a workaround",
    "this workaround",
]:
    if stale in func:
        raise SystemExit(f"SREV-077 failed: stale source comment still contains {stale!r}")

if func.index("if (! ins)") > func.index("if (ins[1]"):
    raise SystemExit("SREV-077 failed: NULL insert-array gate is after ins[1] dereference")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "### SREV-077: FormatMessage Insert Array Gate",
    "FORMAT_MESSAGE_INSERT_ARRAY_GATE",
    "srev-077-format-message-insert-gate.schema.json",
]:
    require(ledger, term, "ledger")

print("SREV-077 schema/source gate passed")
