#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-056 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-056 failed: {label} still contains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-056-file-del-path-tree-buffer.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-056 failed: schema is not draft-07")
if schema.get("id") != "FILE_DEL_PATH_TREE_BUFFER":
    raise SystemExit("SREV-056 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "fixed 0x7FFF + 1 WCHAR buffer",
    "Length + 1 is below PathCapacity",
    "component plus NUL fits in PathCapacity",
    "path buffer allocation must be checked",
    "non-null non-empty NUL-terminated NtPath",
    "DOS path allocation must be checked before wcscpy",
]:
    require(contracts, term, "schema")

src = (ROOT / "Sandboxie/core/dll/file_del.c").read_text()
spec = (ROOT / "docs/plan/srev-056-file-del-path-tree-buffer.md").read_text()
ledger = read_combined_ledger(ROOT)

for term in [
    "File_SavePathNode_internal(HANDLE hPathsFile, LIST* parent, WCHAR* Path, ULONG Length, ULONG PathCapacity, ULONG SetFlags",
    "if (Length + 1 >= PathCapacity)\n        return;",
    "if (child->name_len >= PathCapacity - Length) {",
    "child = List_Next(child);\n            continue;",
    "File_SavePathNode_internal(hPathsFile, &child->items, Path, Path_Len, PathCapacity, SetFlags | child->flags, TranslatePath);",
    "ULONG PathCapacity = 0x7FFF + 1; // max nt path plus terminator",
    "WCHAR* Path = (WCHAR *)Dll_Alloc(PathCapacity * sizeof(WCHAR));",
    "if (!Path) {\n        NtClose(hPathsFile);\n        return;\n    }",
    "File_SavePathNode_internal(hPathsFile, Root, Path, 0, PathCapacity, 0, TranslatePath);",
    "if (!NtPath || !*NtPath)\n        return NULL;",
    "DosPath = Dll_Alloc(len_nt * sizeof(WCHAR));\n    if (!DosPath)\n        return NULL;",
]:
    require(src, term, "file_del source")

reject(src, "File_SavePathNode_internal(hPathsFile, Root, Path, 0, 0, TranslatePath);", "file_del source")
reject(src, "WCHAR* Path = (WCHAR *)Dll_Alloc((0x7FFF + 1)*sizeof(WCHAR));", "file_del source")
reject(src, "DosPath = Dll_Alloc(len_nt * sizeof(WCHAR));\n    wcscpy(DosPath, NtPath);", "file_del source")

for term in [
    "https://learn.microsoft.com/en-us/cpp/c-runtime-library/unicode-the-wide-character-set",
    "https://learn.microsoft.com/en-us/cpp/c-runtime-library/reference/strchr-wcschr-mbschr-mbschr-l",
    "https://learn.microsoft.com/en-us/cpp/c-runtime-library/reference/memmove-wmemmove",
    "srev-056-file-del-path-tree-buffer.schema.json",
]:
    require(spec, term, "spec")

for term in [
    "### SREV-056: File Delete Path Tree Buffer Boundary",
    "FILE_DEL_PATH_TREE_BUFFER",
    "srev-056-file-del-path-tree-buffer.schema.json",
]:
    require(ledger, term, "ledger")

print("SREV-056 schema/source gate passed")
