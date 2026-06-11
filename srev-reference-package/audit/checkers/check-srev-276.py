#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-276 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-276 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-276-nt-to-dos-namespace-boundary.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-276 failed: schema is not draft-07")
if schema.get("id") != "NT_TO_DOS_NAMESPACE_BOUNDARY":
    raise SystemExit("SREV-276 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/dll/file.c":
    raise SystemExit("SREV-276 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "caller-visible path presentation",
    "MS-DOS device names are object-namespace junctions",
    "mappings must come from known namespace links",
    "hidden Sandboxie NT box roots may be projected",
    "MUP NT paths may be projected to UNC-like",
    "generic NT device paths must not be rewritten",
    "disabled Device-to-dot-device fallback remains disabled",
    "this SREV changes comments and proof only",
]:
    require(contracts, term, "schema")

src = (ROOT / "Sandboxie/core/dll/file.c").read_text()
spec = (ROOT / "docs/plan/srev-276-nt-to-dos-namespace-boundary.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-276.md").read_text()

start = src.index("_FX BOOLEAN SbieDll_TranslateNtToDosPath(")
end = src.index("// File_GetTruePathForBoxedPath", start)
translate = src[start:end]

for term in [
    "if (_wcsnicmp(path, L\"\\\\??\\\\\", 4) == 0)",
    "if (_wcsnicmp(path, File_Mup, File_MupLen) == 0)",
    "SREV-276: if the caller-visible DOS sandbox root is configured",
    "the hidden NT box root back to that DOS root before generic drive lookup.",
    "Dll_BoxFileDosPathLen && Dll_BoxFilePathLen <= path_len",
    "wmemmove(path + Dll_BoxFileDosPathLen",
    "wmemcpy(path, Dll_BoxFileDosPath, Dll_BoxFileDosPathLen);",
    "drive = File_GetDriveForPath(path, path_len);",
    "drive = File_GetDriveForUncPath(path, path_len, &prefix_len);",
    "SREV-276: do not invent a generic \\Device\\ -> \\\\.\\ fallback here.",
    "Win32 device names are DOS-device namespace links, not a lossless",
    "replacement for every NT device path",
    "known Chrome handler compatibility trap.",
    "/*if (_wcsnicmp(path, L\"\\\\Device\\\\\", 8) == 0)",
    "return FALSE;",
]:
    require(translate, term, "translate source block")

for stale in [
    "workaround for hidden box root",
    "sometimes we have to use a path which has no drive letter",
    "Note: fix me this makes chrome crash handler hang",
]:
    reject(translate, stale, "translate stale comment")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "### SREV-276: NT-To-DOS Namespace Boundary",
    "NT_TO_DOS_NAMESPACE_BOUNDARY",
    "srev-276-nt-to-dos-namespace-boundary.schema.json",
    "Sandboxie/core/dll/file.c",
    "SbieDll_TranslateNtToDosPath",
    "QueryDosDevice",
    "MS-DOS device",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-276 source gate passed")
