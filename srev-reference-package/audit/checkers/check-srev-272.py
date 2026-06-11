#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-272 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-272 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-272-file-query-by-name-delete-mark-class-gate.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-272 failed: schema is not draft-07")
if schema.get("id") != "FILE_QUERY_BY_NAME_DELETE_MARK_CLASS_GATE":
    raise SystemExit("SREV-272 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/dll/file.c":
    raise SystemExit("SREV-272 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "output layout is owned by FileInformationClass",
    "inspect CreationTime only for classes",
    "Length covers that field",
    "must not be treated as FILE_BASIC_INFORMATION for all query-by-name classes",
    "commented legacy check remains disabled",
]:
    require(contracts, term, "schema")

src = (ROOT / "Sandboxie/core/dll/file.c").read_text()
spec = (ROOT / "docs/plan/srev-272-file-query-by-name-delete-mark-class-gate.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-272.md").read_text()

start = src.index("_FX NTSTATUS File_NtQueryInformationByName(")
end = src.index("// File_GetFinalPathNameByHandleW", start)
query_by_name = src[start:end]

for term in [
    "PVOID FileInformation",
    "ULONG Length",
    "FILE_INFORMATION_CLASS FileInformationClass",
    "RtlInitUnicodeString(&objname, CopyPath);",
    "status = __sys_NtQueryInformationByName(",
    "status != STATUS_OBJECT_NAME_NOT_FOUND",
    "status != STATUS_OBJECT_PATH_NOT_FOUND",
    "SREV-272: NtQueryInformationByName returns a class-specific",
    "buffer. Delete-mark filtering cannot treat FileInformation as",
    "FILE_BASIC_INFORMATION unless FileInformationClass proves that",
    "layout and Length covers CreationTime.",
    "/*if (!File_Delete_v2) {",
    "IS_DELETE_MARK(&FileInformation->CreationTime)",
]:
    require(query_by_name, term, "query-by-name source block")

reject(query_by_name, "\n            // todo\n", "bare query-by-name todo")
if "IS_DELETE_MARK(&FileInformation->CreationTime)" not in query_by_name:
    raise SystemExit("SREV-272 failed: legacy delete-mark reference missing")
if "/*if (!File_Delete_v2)" not in query_by_name:
    raise SystemExit("SREV-272 failed: legacy delete-mark check is no longer visibly disabled")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "### SREV-272: File Query-By-Name Delete-Mark Class Gate",
    "FILE_QUERY_BY_NAME_DELETE_MARK_CLASS_GATE",
    "srev-272-file-query-by-name-delete-mark-class-gate.schema.json",
    "Sandboxie/core/dll/file.c",
    "NtQueryInformationByName",
    "FileInformationClass",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-272 source gate passed")
