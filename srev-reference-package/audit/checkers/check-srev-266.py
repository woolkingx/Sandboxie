#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-266 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-266 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-266-file-id-volume-scope-contract.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-266 failed: schema is not draft-07")
if schema.get("id") != "FILE_ID_VOLUME_SCOPE_CONTRACT":
    raise SystemExit("SREV-266 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/dll/file.c":
    raise SystemExit("SREV-266 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "File IDs are scoped to the file system volume",
    "Open-by-id object names are binary reference numbers",
    "paired File_GetName_FromFileId route",
    "true parent directory for boxed roots",
    "does not change XOR shape query classes",
]:
    require(contracts, term, "schema")

src = (ROOT / "Sandboxie/core/dll/file.c").read_text()
spec = (ROOT / "docs/plan/srev-266-file-id-volume-scope-contract.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-266.md").read_text()

start = src.index("_FX NTSTATUS File_GetName_FromFileId(")
end = src.index("// File_MatchPath", start)
from_file_id = src[start:end]

info_start = src.index("else if (FileInformationClass != FileNameInformation)")
info_end = src.index("//\n    // validate buffer length", info_start)
query_info = src[info_start:info_end]

for term in [
    "SREV-266: File IDs are file-system scoped",
    "D:\\sandbox\\drive\\C can target the sandbox volume instead of real C:",
    "Prefer the true parent path before falling back to caller/root handles.",
    "if (ObjectAttributes->ObjectName->Length > 8)",
    "if (ObjectAttributes->ObjectName->Length & 1)",
    "if (! ObjectAttributes->RootDirectory)",
    "SbieDll_GetHandlePath(\n                    ObjectAttributes->RootDirectory, NULL, &IsBoxedPath);",
    "objattrs.RootDirectory = hTrueRoot;",
    "FILE_OPEN_BY_FILE_ID | FILE_SYNCHRONOUS_IO_NONALERT",
    "FileId.LowPart  ^= 0xFFFFFFFF;",
    "FileId.HighPart ^= 0xFFFFFFFF;",
]:
    require(from_file_id, term, "File_GetName_FromFileId")

for stale in [
    "drives have a file with the same FileId.  to workaround this",
    "we always prefer to use the real C: as parent directory",
]:
    reject(from_file_id, stale, "File_GetName_FromFileId comment")

for term in [
    "SREV-266: File IDs are unique only within their file system.",
    "sandboxed file lives under D:\\sandbox\\drive\\C",
    "File_GetName_FromFileId unscramble path.",
    "FileInformationClass == FileInternalInformation",
    "FILE_INTERNAL_INFORMATION *)FileInformation",
    "FileInformationClass == FileAllInformation",
    "InternalInformation.IndexNumber",
    "SbieDll_GetHandlePath(FileHandle, NULL, &IsBoxedPath);",
    "FileId->LowPart  ^= 0xFFFFFFFF;",
    "FileId->HighPart ^= 0xFFFFFFFF;",
]:
    require(query_info, term, "NtQueryInformationFile FileId route")

for stale in [
    "the reason for this is the possibly of files on both C:",
    "to make\n        // this less likely to be a problem, we scrambe the FileId",
]:
    reject(query_info, stale, "NtQueryInformationFile FileId comment")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "### SREV-266: File ID Volume Scope Contract",
    "FILE_ID_VOLUME_SCOPE_CONTRACT",
    "srev-266-file-id-volume-scope-contract.schema.json",
    "Sandboxie/core/dll/file.c",
    "File_GetName_FromFileId",
    "FILE_OPEN_BY_FILE_ID",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-266 source gate passed")
