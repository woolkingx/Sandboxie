#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-270 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-270 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-270-file-msi-config-msi-query-directory-retry.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-270 failed: schema is not draft-07")
if schema.get("id") != "FILE_MSI_CONFIG_MSI_QUERY_DIRECTORY_RETRY":
    raise SystemExit("SREV-270 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/dll/file.c":
    raise SystemExit("SREV-270 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "DLL_IMAGE_MSI_INSTALLER after STATUS_OBJECT_NAME_NOT_FOUND",
    "Length == 34",
    "MaximumLength must prove room for the trailing NUL",
    "length-bounded",
    "does not change the MSI image gate status gate target path shape",
]:
    require(contracts, term, "schema")

src = (ROOT / "Sandboxie/core/dll/file.c").read_text()
spec = (ROOT / "docs/plan/srev-270-file-msi-config-msi-query-directory-retry.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-270.md").read_text()

start = src.index("_FX NTSTATUS File_NtQueryFullAttributesFile(")
end = src.index("// File_NtQueryFullAttributesFileImpl", start)
query_block = src[start:end]

for term in [
    "UNICODE_STRING *ObjectName = NULL;",
    "if (ObjectAttributes)\n        ObjectName = ObjectAttributes->ObjectName;",
    "status == STATUS_OBJECT_NAME_NOT_FOUND",
    "Dll_ImageType == DLL_IMAGE_MSI_INSTALLER",
    "ObjectName != NULL",
    "ObjectName->Buffer && ObjectName->Length == 34",
    "ObjectName->MaximumLength >= ObjectName->Length + sizeof(WCHAR)",
    "ObjectName->Buffer[ObjectName->Length / sizeof(WCHAR)] == L'\\0'",
    "_wcsnicmp(ObjectName->Buffer + 6, L\"\\\\Config.Msi\", 11) == 0",
    "SREV-270: this MSI Config.Msi compatibility retry passes ObjectName",
    "MaximumLength proves a trailing NUL beyond Length.",
    "CreateDirectory(ObjectName->Buffer, NULL);",
    "status = File_NtQueryFullAttributesFileImpl(ObjectAttributes, FileInformation);",
]:
    require(query_block, term, "MSI Config.Msi retry source block")

reject(query_block, "_wcsicmp(ObjectAttributes->ObjectName->Buffer + 6", "unbounded suffix compare")
reject(query_block, "CreateDirectory(ObjectAttributes->ObjectName->Buffer, NULL)", "ungated CreateDirectory pointer")
reject(query_block, "MSI bug: this must not fail", "stale comment")

if query_block.count("File_NtQueryFullAttributesFileImpl(ObjectAttributes, FileInformation)") != 2:
    raise SystemExit("SREV-270 failed: expected initial query plus one retry")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "### SREV-270: File MSI Config.Msi Query Directory Retry",
    "FILE_MSI_CONFIG_MSI_QUERY_DIRECTORY_RETRY",
    "srev-270-file-msi-config-msi-query-directory-retry.schema.json",
    "Sandboxie/core/dll/file.c",
    "CreateDirectory",
    "UNICODE_STRING",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-270 source gate passed")
