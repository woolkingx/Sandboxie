#!/usr/bin/env python3
import json
from pathlib import Path

from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-237 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-237 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-237-dump-header-topology.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-237 failed: schema is not draft-07")
if schema.get("id") != "DUMP_HEADER_TOPOLOGY_CONTRACT":
    raise SystemExit("SREV-237 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/dll/dump.h":
    raise SystemExit("SREV-237 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "DLL minidump helper declaration header",
    "may declare Dump_Init",
    "does not own DbgHelp loading MiniDumpWriteDump function-pointer resolution",
    "Runtime behavior changes belong to dump.c dllmain.c SboxDll.vcxproj",
    "caller topology and concrete runtime owner",
]:
    require(contracts, term, "schema contract")

spec = (ROOT / "docs/plan/srev-237-dump-header-topology.md").read_text()
header = (ROOT / "Sandboxie/core/dll/dump.h").read_text()
dump = (ROOT / "Sandboxie/core/dll/dump.c").read_text()
dllmain = (ROOT / "Sandboxie/core/dll/dllmain.c").read_text()
project = (ROOT / "Sandboxie/core/dll/SboxDll.vcxproj").read_text()
srev156_spec = (ROOT / "docs/plan/srev-156-dump-dbghelp-entry-and-client-pointers.md").read_text()
ledger = read_combined_ledger(ROOT)
fragment = (ROOT / "docs/plan/ledger/srev-237.md").read_text()

require(header, "int Dump_Init(void);", "header declaration")

for forbidden in [
    "LoadLibrary",
    "GetProcAddress",
    "MiniDumpWriteDump",
    "MINIDUMP_EXCEPTION_INFORMATION",
    "SetUnhandledExceptionFilter",
    "SBIEDLL_HOOK",
    "EnableMiniDump",
    "MiniDumpFlags",
    "DbgHelp",
]:
    reject(header, forbidden, "runtime owner code in header")

for term in [
    '#include "dump.h"',
    "typedef BOOL (__stdcall *P_MiniDumpWriteDump)(",
    "static P_MiniDumpWriteDump __sys_MiniDumpWriteDump;",
    "static HMODULE Dump_DbgHelpMod;",
    "static LONG __stdcall Dump_CrashHandlerExceptionFilter(EXCEPTION_POINTERS* pEx)",
    "stMDEI.ThreadId = GetCurrentThreadId();",
    "stMDEI.ExceptionPointers = pEx;",
    "stMDEI.ClientPointers = FALSE;",
    "if (__sys_MiniDumpWriteDump &&",
    "__sys_MiniDumpWriteDump(GetCurrentProcess(), GetCurrentProcessId(), hFile, Dump_Flags, &stMDEI, NULL, NULL)",
    "_FX int Dump_Init(void)",
    "Dump_DbgHelpMod = LoadLibrary(L\"dbghelp.dll\");",
    "__sys_MiniDumpWriteDump = (P_MiniDumpWriteDump)GetProcAddress(Dump_DbgHelpMod, \"MiniDumpWriteDump\");",
    "if (! __sys_MiniDumpWriteDump) {",
    "SetUnhandledExceptionFilter(Dump_CrashHandlerExceptionFilter);",
    "SBIEDLL_HOOK(Dump_, SetUnhandledExceptionFilter);",
]:
    require(dump, term, "dump.c owner topology")

missing = dump.index("if (! __sys_MiniDumpWriteDump) {")
install = dump.index("SetUnhandledExceptionFilter(Dump_CrashHandlerExceptionFilter);")
if missing > install:
    raise SystemExit("SREV-237 failed: MiniDumpWriteDump missing-export gate is not before handler install")

for term in [
    '#include "dump.h"',
    'Config_GetSettingsForImageName_bool(L"EnableMiniDump", FALSE)',
    "Dump_Init();",
]:
    require(dllmain, term, "dllmain caller topology")

for term in [
    '<ClCompile Include="dump.c" />',
    '<ClInclude Include="dump.h" />',
]:
    require(project, term, "project build topology")

for term in [
    "SREV-156: Dump DbgHelp Entry And Client Pointers",
    "owner: Sandboxie/core/dll/dump.c",
    "MiniDumpWriteDump",
    "ClientPointers",
    "SetUnhandledExceptionFilter",
    "Windows minidump creation and DbgHelp failure runtime proof",
]:
    require(ledger, term, "existing dump owner coverage")

for term in [
    "GetProcAddress",
    "MiniDumpWriteDump",
    "MINIDUMP_EXCEPTION_INFORMATION",
    "SetUnhandledExceptionFilter",
]:
    require(srev156_spec, term, "SREV-156 official shape")

for term in [
    "No source patch",
    "declaration/topology header",
    "No new Windows/API runtime behavior is defined by this header",
    "concrete-owner SREV Windows gates",
]:
    require(spec, term, "spec classification")

for term in [
    "kind: srev-ledger-entry",
    "id: SREV-237",
    "owner: Sandboxie/core/dll/dump.h",
    "docs-only-source-topology-reviewed",
    "srev-237-dump-header-topology.schema.json",
    "check-srev-237.py",
]:
    require(fragment, term, "ledger fragment")
    require(ledger, term, "combined ledger")

print("SREV-237 source gate passed")
