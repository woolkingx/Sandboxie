#!/usr/bin/env python3
import json
from pathlib import Path

from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-236 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-236 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-236-debug-header-topology.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-236 failed: schema is not draft-07")
if schema.get("id") != "DEBUG_HEADER_TOPOLOGY_CONTRACT":
    raise SystemExit("SREV-236 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/dll/debug.h":
    raise SystemExit("SREV-236 failed: wrong owner")

official_refs = "\n".join(schema["official_references"])
for term in [
    "nf-debugapi-isdebuggerpresent",
    "nf-debugapi-outputdebugstringw",
    "nf-synchapi-sleep",
    "nf-debugapi-debugbreak",
]:
    require(official_refs, term, "official reference")

contracts = "\n".join(schema["contracts"])
for term in [
    "DLL debug helper declaration header",
    "Debug_Wait conditionally declare Debug_Init",
    "does not own debugger wait policy config reads debug hook installation",
    "Runtime behavior changes belong to debug.c dllmain.c or SboxDll.vcxproj",
    "caller topology and concrete runtime owner",
]:
    require(contracts, term, "schema contract")

spec = (ROOT / "docs/plan/srev-236-debug-header-topology.md").read_text()
header = (ROOT / "Sandboxie/core/dll/debug.h").read_text()
debug = (ROOT / "Sandboxie/core/dll/debug.c").read_text()
dllmain = (ROOT / "Sandboxie/core/dll/dllmain.c").read_text()
project = (ROOT / "Sandboxie/core/dll/SboxDll.vcxproj").read_text()
ledger = read_combined_ledger(ROOT)
fragment = (ROOT / "docs/plan/ledger/srev-236.md").read_text()

for term in [
    "void Debug_Wait();",
    "#ifdef  WITH_DEBUG",
    '#define  BREAK_IMAGE_1      L"TestTarget.exe"',
    "int Debug_Init(void);",
    "#endif  WITH_DEBUG",
]:
    require(header, term, "header declaration")

for forbidden in [
    "SbieApi_QueryConfBool",
    "IsDebuggerPresent",
    "OutputDebugString",
    "Sleep(",
    "__debugbreak",
    "SBIEDLL_HOOK",
    "DbgPrint",
    "DbgTrace",
    "GetProcAddress",
    "WaitForDebugEvent",
]:
    reject(header, forbidden, "runtime owner code in header")

for term in [
    '#include "debug.h"',
    "_FX void Debug_Wait()",
    'SbieApi_QueryConfBool(NULL, L"WaitForDebuggerAll", FALSE)',
    'SbieDll_CheckStringInList(Dll_ImageName, NULL, L"WaitForDebugger")',
    'SbieApi_QueryConfAsIs(NULL, L"WaitForDebuggerCmdLine"',
    "while (!IsDebuggerPresent())",
    'OutputDebugString(L"Waiting for Debugger\\n");',
    'SbieApi_QueryConfBool(NULL, L"WaitForDebuggerSilent", TRUE)',
    "__debugbreak();",
    "#ifdef WITH_DEBUG",
    "_FX int Debug_Init(void)",
    "#if defined(BREAK_IMAGE_1)",
    "_wcsicmp(Dll_ImageName, BREAK_IMAGE_1)",
    "void DbgPrint(const char* format, ...)",
    "void DbgTrace(const char* format, ...)",
]:
    require(debug, term, "debug.c owner topology")

disabled_block_start = debug.index("#if 0", debug.index("Debug_Init"))
break_image_use = debug.index("#if defined(BREAK_IMAGE_1)")
if disabled_block_start > break_image_use:
    raise SystemExit("SREV-236 failed: BREAK_IMAGE_1 use is not in disabled debug block")

for term in [
    '#include "debug.h"',
    "Debug_Wait();",
    "#ifdef WITH_DEBUG",
    "ok = Debug_Init();",
    "#endif WITH_DEBUG",
]:
    require(dllmain, term, "dllmain caller topology")

for term in [
    "WITH_DEBUG;%(PreprocessorDefinitions)",
    '<ClCompile Include="debug.c" />',
    '<ClInclude Include="debug.h" />',
]:
    require(project, term, "project build topology")

for term in [
    "SREV-146: Debug Format Buffer Termination",
    "owner: Sandboxie/core/dll/debug.c",
    "SboxDll.vcxproj` defines `WITH_DEBUG`",
    "DbgPrint",
    "DbgTrace",
]:
    require(ledger, term, "existing debug owner coverage")

for term in [
    "No source patch",
    "declaration/topology header",
    "they do not make `debug.h` the owner of that behavior",
    "concrete-owner SREV Windows gates",
]:
    require(spec, term, "spec classification")

for term in [
    "kind: srev-ledger-entry",
    "id: SREV-236",
    "owner: Sandboxie/core/dll/debug.h",
    "docs-only-source-topology-reviewed",
    "srev-236-debug-header-topology.schema.json",
    "check-srev-236.py",
]:
    require(fragment, term, "ledger fragment")
    require(ledger, term, "combined ledger")

print("SREV-236 source gate passed")
