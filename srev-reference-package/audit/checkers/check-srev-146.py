#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-146 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-146 failed: {label} still contains {needle!r}")


def function_body(text: str, name: str) -> str:
    marker = f"void {name}(const char* format, ...)"
    start = text.index(marker)
    next_marker = text.find("\n//---------------------------------------------------------------------------", start + len(marker))
    if next_marker == -1:
        return text[start:]
    return text[start:next_marker]


schema = json.loads(
    (ROOT / "docs/plan/srev-146-debug-format-buffer-termination.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-146 failed: schema is not draft-07")
if schema.get("id") != "DEBUG_FORMAT_BUFFER_TERMINATION":
    raise SystemExit("SREV-146 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "DbgPrint and DbgTrace own the local debug-format buffer before passing it to string-consuming debug or monitor APIs",
    "_vsnprintf is a counted writer but does not guarantee null termination when output is truncated",
    "The local buffer must reserve one byte for a terminator by passing sizeof(tmp1) - 1 as the count",
    "The local buffer must be initialized before _vsnprintf and must have the final byte set to '\\0' after _vsnprintf",
    "This SREV does not change debug hook installation, monitor categories, trace routing, or any non-debug sandbox policy decision",
]:
    require(contracts, term, "schema")

debug_c = (ROOT / "Sandboxie/core/dll/debug.c").read_text()
vcxproj = (ROOT / "Sandboxie/core/dll/SboxDll.vcxproj").read_text()
spec = (ROOT / "docs/plan/srev-146-debug-format-buffer-termination.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-146.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

require(vcxproj, "<PreprocessorDefinitions>WITH_DEBUG;%(PreprocessorDefinitions)</PreprocessorDefinitions>", "WITH_DEBUG project definition")

dbg_print = function_body(debug_c, "DbgPrint")
dbg_trace = function_body(debug_c, "DbgTrace")

for body, label, consumer in [
    (dbg_print, "DbgPrint", "OutputDebugStringA(tmp1);"),
    (dbg_trace, "DbgTrace", "Sbie_snwprintf((WCHAR *)tmp2, sizeof(tmp2)/sizeof(WCHAR), L\"%S\", tmp1);"),
]:
    require(body, "char tmp1[510];", label)
    require(body, "tmp1[0] = '\\0';", label)
    require(body, "P_vsnprintf(tmp1, sizeof(tmp1) - 1, format, va_args);", label)
    require(body, "tmp1[sizeof(tmp1) - 1] = '\\0';", label)
    require(body, consumer, label)
    reject(body, "P_vsnprintf(tmp1, sizeof(tmp1), format, va_args);", label)

for term in [
    "Sandboxie/core/dll/debug.c",
    "### SREV-146: Debug Format Buffer Termination",
    "DEBUG_FORMAT_BUFFER_TERMINATION",
    "srev-146-debug-format-buffer-termination.schema.json",
    "DbgPrint",
    "DbgTrace",
    "P_vsnprintf",
    "OutputDebugStringA",
    "SbieApi_MonitorPutMsg",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-146 schema/source gate passed")
