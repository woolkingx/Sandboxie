#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-155 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-155 failed: {label} still contains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-155-file-xlat-counted-object-name.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-155 failed: schema is not draft-07")
if schema.get("id") != "FILE_XLAT_COUNTED_OBJECT_NAME":
    raise SystemExit("SREV-155 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "OBJECT_NAME_INFORMATION.Name is a counted UNICODE_STRING",
    "UNICODE_STRING.Length is a byte count",
    "does not include a trailing null character",
    "derive CACHE_PATH destination length from Name->Name.Length",
    "Name->Name.Length must be WCHAR-aligned",
    "trailing backslash trimming must stay within the counted Name->Name.Buffer extent",
    "does not change File_ReparsePointsBusy KPATH-002 wait behavior",
    "Linux source gate is not Windows runtime proof",
]:
    require(contracts, term, "schema")

source = (ROOT / "Sandboxie/core/drv/file_xlat.c").read_text()
spec = (ROOT / "docs/plan/srev-155-file-xlat-counted-object-name.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-155.md").read_text()
kpath002 = (ROOT / "docs/plan/2026-05-27-sandboxie-kernel-path-audit.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "File_TranslateReparsePoints_3",
    "ZwCreateFile(",
    "FILE_DIRECTORY_FILE | FILE_SYNCHRONOUS_IO_NONALERT",
    "ObReferenceObjectByHandle(",
    "*IoFileObjectType, KernelMode",
    "Obj_GetName(pool, object, &Name, &NameLength);",
    "if (Name && (Name != &Obj_Unnamed) &&",
    "Name->Name.Buffer &&",
    "(Name->Name.Length % sizeof(WCHAR)) == 0",
    "dst_len = Name->Name.Length / sizeof(WCHAR);",
    "while (dst_len && Name->Name.Buffer[dst_len - 1] == L'\\\\')",
    "wmemcpy(entry->dst, Name->Name.Buffer, dst_len);",
    "entry->dst[dst_len] = L'\\0';",
    "File_ReparsePointsBusy",
]:
    require(source, term, "file_xlat.c")

reject(source, "dst_len = wcslen(path3);", "C-string object-name length")
reject(source, "WCHAR *path3 = Name->Name.Buffer;", "stale object-name C-string alias")

name_gate = source.index("if (Name && (Name != &Obj_Unnamed) &&")
copy = source.index("wmemcpy(entry->dst, Name->Name.Buffer, dst_len);")
if name_gate > copy:
    raise SystemExit("SREV-155 failed: counted object-name gate appears after cache copy")

for term in [
    "Global Busy Wait Around Synchronous File I/O",
    "File_ReparsePointsBusy",
    "bounded waiting",
    "runtime proof",
]:
    require(kpath002, term, "KPATH-002 separation")

for term in [
    "### SREV-155: File Reparse Cache Counted Object Name",
    "FILE_XLAT_COUNTED_OBJECT_NAME",
    "srev-155-file-xlat-counted-object-name.schema.json",
    "Sandboxie/core/drv/file_xlat.c",
    "File_TranslateReparsePoints_3",
    "OBJECT_NAME_INFORMATION.Name",
    "UNICODE_STRING.Length",
    "Name->Name.Length",
    "KPATH-002",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-155 schema/source gate passed")
