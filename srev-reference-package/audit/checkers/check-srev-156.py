#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-156 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-156 failed: {label} still contains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-156-dump-dbghelp-entry-and-client-pointers.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-156 failed: schema is not draft-07")
if schema.get("id") != "DUMP_DBGHELP_ENTRY_AND_CLIENT_POINTERS":
    raise SystemExit("SREV-156 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "GetProcAddress returns NULL on failure",
    "must not be called through a NULL function pointer",
    "must not install Dump_CrashHandlerExceptionFilter unless MiniDumpWriteDump is resolved",
    "frees Dump_DbgHelpMod clears the module handle and returns 0",
    "guard the function-pointer call before MiniDumpWriteDump",
    "ClientPointers is FALSE for local exception pointers",
    "does not change MiniDumpFlags dump file path SetUnhandledExceptionFilter blocking policy",
    "Linux source gate is not Windows runtime proof",
]:
    require(contracts, term, "schema")

source = (ROOT / "Sandboxie/core/dll/dump.c").read_text()
settings = (ROOT / "Sandboxie/install/SbieSettings.ini").read_text()
spec = (ROOT / "docs/plan/srev-156-dump-dbghelp-entry-and-client-pointers.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-156.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "Dump_CrashHandlerExceptionFilter",
    "Dump_Init",
    "LoadLibrary(L\"dbghelp.dll\")",
    "GetProcAddress(Dump_DbgHelpMod, \"MiniDumpWriteDump\")",
    "if (! __sys_MiniDumpWriteDump) {",
    "FreeLibrary(Dump_DbgHelpMod);",
    "Dump_DbgHelpMod = NULL;",
    "return 0;",
    "SetUnhandledExceptionFilter(Dump_CrashHandlerExceptionFilter);",
    "SBIEDLL_HOOK(Dump_, SetUnhandledExceptionFilter);",
    "stMDEI.ThreadId = GetCurrentThreadId();",
    "stMDEI.ExceptionPointers = pEx;",
    "stMDEI.ClientPointers = FALSE;",
    "if (__sys_MiniDumpWriteDump &&",
    "__sys_MiniDumpWriteDump(GetCurrentProcess(), GetCurrentProcessId(), hFile, Dump_Flags, &stMDEI, NULL, NULL)",
    "MiniDumpFlags",
    "DUMP_FLAGS_DEFAULT",
    "DUMP_FLAGS_EXTENDED",
]:
    require(source, term, "dump.c")

reject(source, "stMDEI.ClientPointers = TRUE;", "remote-client pointer shape")
reject(
    source,
    "if (__sys_MiniDumpWriteDump(GetCurrentProcess(), GetCurrentProcessId(), hFile, Dump_Flags, &stMDEI, NULL, NULL))",
    "unguarded minidump call",
)

resolve = source.index("__sys_MiniDumpWriteDump = (P_MiniDumpWriteDump)GetProcAddress")
missing = source.index("if (! __sys_MiniDumpWriteDump) {", resolve)
install = source.index("SetUnhandledExceptionFilter(Dump_CrashHandlerExceptionFilter);")
if not (resolve < missing < install):
    raise SystemExit("SREV-156 failed: MiniDumpWriteDump missing-export gate is not before handler install")

missing_block = source[missing:install]
for term in [
    "FreeLibrary(Dump_DbgHelpMod);",
    "Dump_DbgHelpMod = NULL;",
    "return 0;",
]:
    require(missing_block, term, "missing-export cleanup")

for term in [
    "[MiniDumpFlags]",
    "Requirements=<EnableMiniDump>",
    "Syntax=[sn]=Extended|0xAABBCCDD",
]:
    require(settings, term, "settings")

for term in [
    "### SREV-156: Dump DbgHelp Entry And Client Pointers",
    "DUMP_DBGHELP_ENTRY_AND_CLIENT_POINTERS",
    "srev-156-dump-dbghelp-entry-and-client-pointers.schema.json",
    "Sandboxie/core/dll/dump.c",
    "MiniDumpWriteDump",
    "GetProcAddress",
    "ClientPointers",
    "SetUnhandledExceptionFilter",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-156 schema/source gate passed")
