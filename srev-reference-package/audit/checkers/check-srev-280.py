#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-280 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-280 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-280-box-root-raw-path-fallback-owner.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-280 failed: schema is not draft-07")
if schema.get("id") != "BOX_ROOT_RAW_PATH_FALLBACK_OWNER":
    raise SystemExit("SREV-280 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/dll/file_init.c":
    raise SystemExit("SREV-280 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "box-root raw-path fallback publication",
    "namespace-specific presentations",
    "MS-DOS device names are object-namespace junctions",
    "QueryDosDevice exposes MS-DOS device namespace mappings",
    "local and global DosDevices contexts",
    "driver-published box root only after normal DOS projection misses",
    "reuse SbieDll_TranslateNtToDosPath",
    "SREV-057 owns raw-root byte-capacity",
    "SREV-276 owns the NT-to-DOS namespace translator",
    "this SREV changes comments and proof only",
]:
    require(contracts, term, "schema")

src = (ROOT / "Sandboxie/core/dll/file_init.c").read_text()
spec = (ROOT / "docs/plan/srev-280-box-root-raw-path-fallback-owner.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-280.md").read_text()
srev_057 = (ROOT / "docs/plan/ledger/srev-057.md").read_text()
srev_057_schema = (ROOT / "docs/plan/srev-057-file-init-box-root-path.schema.json").read_text()
srev_276 = (ROOT / "docs/plan/ledger/srev-276.md").read_text()

start = src.index("Dll_BoxFileDosPath = Dll_Alloc((Dll_BoxFilePathLen + 1) * sizeof(WCHAR));")
end = src.index("File_InitSnapshots();", start)
init = src[start:end]

for term in [
    "Dll_BoxFileDosPath = Dll_Alloc((Dll_BoxFilePathLen + 1) * sizeof(WCHAR));",
    "wcscpy((WCHAR *)Dll_BoxFileDosPath, Dll_BoxFilePath);",
    "SbieDll_TranslateNtToDosPath((WCHAR *)Dll_BoxFileDosPath)",
    "if (!Dll_BoxFileDosPath)\n    {",
    "SREV-280: if the normal box root lacks a caller-visible DOS",
    "presentation, query the driver-published raw root and run the",
    "same NT-to-DOS namespace translator before publishing lengths.",
    "SbieApi_QueryProcessInfoStr(0, 'root', NULL, &BoxFileRawPathLen)",
    "BoxFileRawPathLen >= sizeof(WCHAR) && BoxFileRawPathLen <= 0xFFFF",
    "WCHAR* BoxFileRawPath = Dll_AllocTemp(BoxFileRawPathLen);",
    "SbieApi_QueryProcessInfoStr(0, 'root', BoxFileRawPath, &BoxFileRawPathLen)",
    "Dll_BoxFileRawPath = BoxFileRawPath;",
    "Dll_BoxFileRawPathLen = wcslen(Dll_BoxFileRawPath);",
    "Dll_BoxFileDosPath = Dll_Alloc(BoxFileRawPathLen);",
    "wcscpy((WCHAR*)Dll_BoxFileDosPath, Dll_BoxFileRawPath);",
    "SbieDll_TranslateNtToDosPath((WCHAR*)Dll_BoxFileDosPath)",
    "if(Dll_BoxFileDosPath)\n        Dll_BoxFileDosPathLen = wcslen(Dll_BoxFileDosPath);",
]:
    require(init, term, "file_init source block")

for stale in [
    "the root is redirected with a reparse point and the target device does not have a drvie letter",
    "implement workaround, see SbieDll_TranslateNtToDosPath",
]:
    reject(init, stale, "file_init raw-root fallback comment")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "driver-published raw box root",
    "same NT-to-DOS translator",
    "SREV-057 owns the allocation, byte-capacity, and global-publication gates",
    "SREV-276 owns the namespace translator",
    "BOX_ROOT_RAW_PATH_FALLBACK_OWNER",
    "srev-280-box-root-raw-path-fallback-owner.schema.json",
]:
    require(spec, term, "spec")

for term in [
    "Dll_BoxFileRawPath is published only after allocation, query success, and non-empty string proof",
    "The raw-root fallback accepts only byte capacities that fit UNICODE_STRING.MaximumLength",
]:
    require(srev_057_schema, term, "SREV-057 schema adjacency")

for term in [
    "FILE_INIT_BOX_ROOT_PATH_PUBLICATION",
    "source string, allocation, query status, byte-capacity, and non-empty string gates",
]:
    require(srev_057, term, "SREV-057 ledger adjacency")

for term in [
    "SbieDll_TranslateNtToDosPath",
    "MS-DOS device names are object-namespace junctions",
    "generic NT device paths must not be rewritten",
]:
    require(srev_276, term, "SREV-276 adjacency")

for term in [
    "### SREV-280: Box Root Raw Path Fallback Owner",
    "BOX_ROOT_RAW_PATH_FALLBACK_OWNER",
    "srev-280-box-root-raw-path-fallback-owner.schema.json",
    "Sandboxie/core/dll/file_init.c",
    "SbieDll_TranslateNtToDosPath",
    "SREV-057",
    "SREV-276",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-280 source gate passed")
