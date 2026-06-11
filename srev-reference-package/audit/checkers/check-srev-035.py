#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-035 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-035 failed: {label} still contains {needle!r}")


schema = json.loads((ROOT / "docs/plan/srev-035-file-api-rename-wire.schema.json").read_text())
if schema.get("id") != "FILE_API_RENAME_COUNTED_STRING":
    raise SystemExit("SREV-035 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "UNICODE_STRING64.Length is a byte count",
    "UNICODE_STRING64.Length must be nonzero, <= 32000, and <= MaximumLength",
    "embedded NUL is invalid",
    "target_name is copied into FILE_RENAME_INFORMATION as a simple relative file name",
    "FILE_RENAME_INFORMATION.FileNameLength is a byte count",
    "frees the path buffer before returning",
]:
    require(contracts, term, "schema")

src = (ROOT / "Sandboxie/core/drv/file.c").read_text()
spec = (ROOT / "docs/plan/srev-035-file-api-rename-wire.md").read_text()
ledger = read_combined_ledger(ROOT)

start = src.index("_FX NTSTATUS File_Api_Rename(")
end = src.index("// File_Api_GetName", start)
rename = src[start:end]

for term in [
    "static BOOLEAN File_Api_RenameContainsWChar(",
    "ULONG count = byte_len / sizeof(WCHAR);",
    "if (text[i] == ch)",
]:
    require(src, term, "counted WCHAR helper")

for term in [
    "user_dir_len = user_uni->Length;",
    "(user_dir_len & (sizeof(WCHAR) - 1))",
    "(user_uni->MaximumLength < user_dir_len)",
    "user_name_len = user_uni->Length;",
    "(user_name_len & (sizeof(WCHAR) - 1))",
    "(user_uni->MaximumLength < user_name_len)",
    "File_Api_RenameContainsWChar(path, user_dir_len, L'\\0')",
    "name = path + (user_dir_len / sizeof(WCHAR));",
    "File_Api_RenameContainsWChar(&name[1], user_name_len, L'\\0')",
    "File_Api_RenameContainsWChar(&name[1], user_name_len, L'\\\\')",
    "Mem_Free(path, path_len);\n        return STATUS_INVALID_PARAMETER;",
]:
    require(rename, term, "File_Api_Rename")

reject(rename, "user_uni->Length & ~1", "File_Api_Rename")
reject(rename, "name = path + wcslen(path);", "File_Api_Rename")
reject(rename, "if (wcschr(&name[1], L'\\\\'))\n        return STATUS_INVALID_PARAMETER;", "File_Api_Rename")

for term in [
    "https://learn.microsoft.com/en-us/windows/win32/api/ntdef/ns-ntdef-_unicode_string",
    "https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-probeforread",
    "https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-zwsetinformationfile",
    "https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/ns-ntifs-_file_rename_information",
    "srev-035-file-api-rename-wire.schema.json",
]:
    require(spec, term, "spec")

for term in [
    "### SREV-035: File API Rename Counted String",
    "File_Api_RenameContainsWChar",
    "srev-035-file-api-rename-wire.schema.json",
]:
    require(ledger, term, "ledger")

print("SREV-035 schema/source gate passed")
