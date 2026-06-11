#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-274 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-274 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-274-file-hard-link-class-boundary.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-274 failed: schema is not draft-07")
if schema.get("id") != "FILE_HARD_LINK_CLASS_BOUNDARY":
    raise SystemExit("SREV-274 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/dll/file.c":
    raise SystemExit("SREV-274 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "FileInformation buffer shape is determined by FileInformationClass",
    "FileLinkInformation creates a hard link with FILE_LINK_INFORMATION",
    "FileLinkInformationEx uses the FILE_LINK_INFORMATION Flags union shape",
    "only classes routed into File_RenameFile hard-link creation",
    "remain native compatibility probes until a class-specific setter contract is proven",
    "failed alternate hard-link probe returns STATUS_INVALID_DEVICE_REQUEST",
    "file_flt.c denies alternate hard-link classes",
    "this SREV changes comments and proof only",
]:
    require(contracts, term, "schema")

src = (ROOT / "Sandboxie/core/dll/file.c").read_text()
flt = (ROOT / "Sandboxie/core/drv/file_flt.c").read_text()
spec = (ROOT / "docs/plan/srev-274-file-hard-link-class-boundary.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-274.md").read_text()

start = src.index("_FX NTSTATUS File_NtSetInformationFile(")
end = src.index("// File_RenameFile", start)
set_info = src[start:end]

for term in [
    "FileInformationClass == FileLinkInformation",
    "FileInformationClass == FileLinkInformationEx",
    "FileInformationClass == FileHardLinkInformation",
    "FileInformationClass == FileHardLinkFullIdInformation",
    "status = File_RenameFile(FileHandle, FileInformation, TRUE);",
    "SREV-274: only FileLinkInformation/Ex have the local",
    "FILE_LINK_INFORMATION create-hard-link path.  Keep these",
    "alternate hard-link classes as a native compatibility probe",
    "unless a class-specific setter contract is proven.",
    "status = __sys_NtSetInformationFile(",
    "FileInformation, Length, FileInformationClass);",
    "status = STATUS_INVALID_DEVICE_REQUEST;",
]:
    require(set_info, term, "set-information source block")

reject(set_info, "else // todo", "hard-link class todo")

for term in [
    "FileInformationClass != FileLinkInformation",
    "FileInformationClass != FileLinkInformationEx",
    "FileInformationClass != FileHardLinkInformation",
    "FileInformationClass != FileHardLinkFullIdInformation",
    "FileInformationClass == FileLinkInformation",
    "FileInformationClass == FileLinkInformationEx",
    "status = File_RenameOperation(proc, Iopb, TRUE);",
    "status = STATUS_ACCESS_DENIED;",
]:
    require(flt, term, "file_flt adjacency")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "### SREV-274: File Hard-Link Class Boundary",
    "FILE_HARD_LINK_CLASS_BOUNDARY",
    "srev-274-file-hard-link-class-boundary.schema.json",
    "Sandboxie/core/dll/file.c",
    "NtSetInformationFile",
    "FILE_LINK_INFORMATION",
    "FileHardLinkInformation",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-274 source gate passed")
