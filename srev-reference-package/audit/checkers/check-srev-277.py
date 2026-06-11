#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-277 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-277 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-277-filepaths-unknown-drive-sentinel.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-277 failed: schema is not draft-07")
if schema.get("id") != "FILEPATHS_UNKNOWN_DRIVE_SENTINEL":
    raise SystemExit("SREV-277 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/dll/file_del.c":
    raise SystemExit("SREV-277 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "save-time path projection",
    "load-time path projection",
    "MS-DOS device namespace links",
    "unavailable drive-letter paths must be preserved",
    "leading-backslash sentinel shape",
    "colon immediately precedes the first path separator",
    "known NT paths still use MUP, drive, or UNC mapping",
    "this SREV changes comments and proof only",
]:
    require(contracts, term, "schema")

src = (ROOT / "Sandboxie/core/dll/file_del.c").read_text()
spec = (ROOT / "docs/plan/srev-277-filepaths-unknown-drive-sentinel.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-277.md").read_text()

save_start = src.index("_FX WCHAR* File_TranslateNtToDosPathForDatFile(")
save_end = src.index("// File_SavePathTree", save_start)
save_block = src[save_start:save_end]

load_start = src.index("_FX WCHAR *File_TranslateDosToNtPathForDatFile(")
load_end = src.index("// File_InitDelete_v2", load_start)
load_block = src[load_start:load_end]

for term in [
    "SREV-277: unavailable drive-letter paths are kept in the tree as",
    "a leading-backslash sentinel, such as L\"\\\\C:\\\\path\", so the",
    "FilePaths.dat round trip can preserve the entry until the drive",
    "mapping exists again.  Strip only that sentinel before writing.",
    "const WCHAR* backslash = wcschr(DosPath+1, L'\\\\');",
    "if (!backslash) backslash = wcschr(DosPath, L'\\0');",
    "if (*(backslash - 1) == L':')",
    "wmemmove(DosPath, DosPath + 1, wcslen(DosPath));",
    "File_GetDriveForPath(DosPath, path_len);",
    "File_GetDriveForUncPath(DosPath, path_len, &prefix_len);",
]:
    require(save_block, term, "save projection block")

for stale in [
    "Hack Hack",
    "drive which does not exist",
    "to not forget it",
]:
    reject(save_block, stale, "unknown-drive stale comment")

for term in [
    "File_GetDriveForLetter(DosPath[0]);",
    "if (drive)",
    "NtPath = File_ConcatPath2(drive->path, drive->len, DosPath, wcslen(DosPath));",
    "return NtPath;",
]:
    require(load_block, term, "load projection block")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "### SREV-277: FilePaths Unknown-Drive Sentinel",
    "FILEPATHS_UNKNOWN_DRIVE_SENTINEL",
    "srev-277-filepaths-unknown-drive-sentinel.schema.json",
    "Sandboxie/core/dll/file_del.c",
    "FilePaths.dat",
    "File_TranslateNtToDosPathForDatFile",
    "unknown-drive sentinel",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-277 source gate passed")
