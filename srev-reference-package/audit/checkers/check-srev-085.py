#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-085 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-085 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-085-pca-restart-command-line-shape.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-085 failed: schema is not draft-07")
if schema.get("id") != "PCA_RESTART_COMMAND_LINE_SHAPE":
    raise SystemExit("SREV-085 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "PCA/job detection",
    "AppContainer processes do not use",
    "system-owned read-only input",
    "sized from the actual command-line length",
    "must not copy a variable-length command line into a fixed local buffer",
    "Digital Guardian detection",
]:
    require(contracts, term, "schema")

dllmain = (ROOT / "Sandboxie/core/dll/dllmain.c").read_text()
proc = (ROOT / "Sandboxie/core/dll/proc.c").read_text()
file_src = (ROOT / "Sandboxie/core/dll/file.c").read_text()
ldr = (ROOT / "Sandboxie/core/dll/ldr.c").read_text()
spec = (ROOT / "docs/plan/srev-085-pca-restart-command-line-shape.md").read_text()
ledger = read_combined_ledger(ROOT)

for term in [
    "Dll_DigitalGuardian = GetModuleHandleA(\"DgApi64.dll\");",
    "Dll_DigitalGuardian = GetModuleHandleA(\"DgApi.dll\");",
    "SREV-085 owns this PCA job restart topology.",
    "PCA job are replaced through SbieSvc before Sandboxie job attach;",
    "AppContainer processes skip this restart path.",
    "SBIE_FLAG_PROCESS_IN_PCA_JOB",
    "SBIE_FLAG_PROCESS_IN_APP_PKG",
    "NoRestartOnPCA",
    "Proc_RestartProcessOutOfPcaJob();",
]:
    require(dllmain, term, "dllmain.c")

for stale in [
    "workaround for Program Compatibility Assistant (PCA)",
    "to start a second instance of this process outside the PCA job",
    "note: restart fails if running as AppContainer",
]:
    reject(dllmain, stale, "dllmain.c PCA comment")

for term in [
    "if (Dll_DigitalGuardian && (PATH_IS_WRITE(mp_flags) || PATH_IS_CLOSED(mp_flags)))",
    "else if (!Dll_DigitalGuardian)",
    "_FX BOOLEAN DigitalGuardian_Init(HMODULE hModule)",
]:
    require(file_src, term, "file.c")

for term in [
    "{ L\"dgapi64.dll\",           DigitalGuardian_Init,           0}",
    "{ L\"dgapi.dll\",             DigitalGuardian_Init,           0}",
]:
    require(ldr, term, "ldr.c")

for term in [
    "const WCHAR *CurrentCommandLine;",
    "SIZE_T CommandLineLen;",
    "CurrentCommandLine = GetCommandLine();",
    "CommandLineLen = wcslen(CurrentCommandLine) + 1;",
    "if (CommandLineLen > ULONG_MAX / sizeof(WCHAR))",
    "CommandLine = Dll_AllocTemp((ULONG)(CommandLineLen * sizeof(WCHAR)));",
    "memcpy(CommandLine, CurrentCommandLine, CommandLineLen * sizeof(WCHAR));",
    "SbieDll_RunSandboxed(L\"\", CommandLine, Directory, 0,",
]:
    require(proc, term, "proc.c")

restart_start = proc.index("_FX void Proc_RestartProcessOutOfPcaJob")
restart_end = proc.index("ExitProcess(0);", restart_start)
restart_block = proc[restart_start:restart_end]
if "Dll_AllocTemp(sizeof(WCHAR) * 8192);\n    wcscpy(CommandLine, GetCommandLine());" in restart_block:
    raise SystemExit("SREV-085 failed: fixed command-line buffer copy remains")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "### SREV-085: PCA Restart Command-Line Shape",
    "PCA_RESTART_COMMAND_LINE_SHAPE",
    "srev-085-pca-restart-command-line-shape.schema.json",
    "SREV-262",
]:
    require(ledger, term, "ledger")

print("SREV-085 schema/source gate passed")
