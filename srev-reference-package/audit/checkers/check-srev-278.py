#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-278 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-278 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-278-directory-enumeration-progress-gate.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-278 failed: schema is not draft-07")
if schema.get("id") != "DIRECTORY_ENUMERATION_PROGRESS_GATE":
    raise SystemExit("SREV-278 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/dll/file_dir.c":
    raise SystemExit("SREV-278 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "progress safety while building the sorted directory merge cache",
    "NtQueryDirectoryFile returns one or more FILE_XXX_INFORMATION records",
    "RestartScan starts enumeration",
    "FILE_ID_BOTH_DIR_INFORMATION is a variable-size record",
    "FileNameLength is a byte count",
    "repeats a name already present in the merge cache",
    "synthesizes STATUS_NO_MORE_FILES before publication",
    "SREV-001 owns variable-size record capacity",
    "this SREV changes comments and proof only",
]:
    require(contracts, term, "schema")

src = (ROOT / "Sandboxie/core/dll/file_dir.c").read_text()
spec = (ROOT / "docs/plan/srev-278-directory-enumeration-progress-gate.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-278.md").read_text()

start = src.index("_FX NTSTATUS File_MergeCache(")
end = src.index("// File_MergeCacheWin2000", start)
merge = src[start:end]

for term in [
    "status = __sys_NtQueryDirectoryFile(",
    "FileIdBothDirectoryInformation",
    "qfile->RestartScan",
    "qfile->RestartScan = FALSE;",
    "len = sizeof(FILE_ID_BOTH_DIR_INFORMATION)",
    "info_ptr->FileNameLength",
    "cache_file->name_uni.Length = (USHORT)info_ptr->FileNameLength;",
    "RtlCompareUnicodeString(",
    "SREV-278: directory enumeration must make progress.",
    "provider repeats a name already present in the merge cache,",
    "synthesize the normal end-of-enumeration status and stop.",
    "if (cmp == 0)",
    "status = STATUS_NO_MORE_FILES;",
    "List_Insert_Before(cache_list, ins_point, cache_file);",
    "List_Insert_After(cache_list, NULL, cache_file);",
    "info_ptr->NextEntryOffset == 0",
]:
    require(merge, term, "merge-cache source block")

if merge.index("if (cmp == 0)") > merge.index("List_Insert_Before(cache_list, ins_point, cache_file);"):
    raise SystemExit("SREV-278 failed: duplicate-name guard must run before cache publication")

for stale in [
    "There is a bug with Isilon drives",
    "always returns STATUS_SUCCESS with the same file name",
    "This causes an infinite loop",
    "assume it is the Isilon bug",
]:
    reject(merge, stale, "directory enumeration stale comment")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

srev_001 = (ROOT / "docs/plan/ledger/srev-001.md").read_text()
for term in [
    "FILE_ID_BOTH_DIR_INFORMATION.FileNameLength",
    "variable-size record",
    "NextEntryOffset",
    "FileNameLength",
]:
    require(srev_001, term, "SREV-001 adjacency")

for term in [
    "### SREV-278: Directory Enumeration Progress Gate",
    "DIRECTORY_ENUMERATION_PROGRESS_GATE",
    "srev-278-directory-enumeration-progress-gate.schema.json",
    "Sandboxie/core/dll/file_dir.c",
    "NtQueryDirectoryFile",
    "STATUS_NO_MORE_FILES",
    "SREV-001",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-278 source gate passed")
