#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-332 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-332 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-332-file-flt-parent-target-context.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-332 failed: schema is not draft-07")
if schema.get("id") != "FILE_FLT_PARENT_TARGET_CONTEXT":
    raise SystemExit("SREV-332 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/drv/file_flt.c":
    raise SystemExit("SREV-332 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "ParentOfTarget is a file object pointer carrier",
    "ParentOfTarget->FileName is not the full target path owner by itself",
    "File_RenameOperation combines ParentOfTarget context with the counted target FileName",
    "RelatedFileObject full-path fallback remains the local topology",
    "SREV-019 length gates remain the counted target-name proof",
    "this SREV changes comments and proof only",
]:
    require(contracts, term, "schema")

src = (ROOT / "Sandboxie/core/drv/file_flt.c").read_text()
spec = (ROOT / "docs/plan/srev-332-file-flt-parent-target-context.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-332.md").read_text()

pre_start = src.index("_FX FLT_PREOP_CALLBACK_STATUS File_PreOperation(")
pre_end = src.index("else if (Iopb->MajorFunction == IRP_MJ_ACQUIRE_FOR_SECTION_SYNCHRONIZATION)", pre_start)
pre_block = src[pre_start:pre_end]

op_start = src.index("_FX NTSTATUS File_RenameOperation(")
op_end = src.index("// File_QueryTeardown", op_start)
op_block = src[op_start:op_end]

for term in [
    "FileInformationClass == FileLinkInformation",
    "FileInformationClass == FileLinkInformationEx",
    "status = File_RenameOperation(proc, Iopb, TRUE);",
    "FileInformationClass == FileRenameInformation",
    "FileInformationClass == FileRenameInformationEx",
    "status = File_RenameOperation(proc, Iopb, FALSE);",
    "SREV-332: ParentOfTarget is a file-object carrier;",
    "File_RenameOperation owns target-context parsing.",
]:
    require(pre_block, term, "set-information routing block")

for term in [
    "FileObject = Parms->SetFileInformation.ParentOfTarget;",
    "if ((! FileObject) || (! infoL))",
    "if ((! FileObject) || (! infoR))",
    "File_CheckRenameLinkNameLength(",
    "FIELD_OFFSET(FILE_LINK_INFORMATION, FileName)",
    "FIELD_OFFSET(FILE_RENAME_INFORMATION, FileName)",
    "FileObject->FileName.Buffer[0] != L'\\\\'",
    "PFILE_OBJECT RelatedFileObject = FileObject->RelatedFileObject;",
    "FileObject = RelatedFileObject;",
    "MyContext.Options = IO_OPEN_TARGET_DIRECTORY;",
    "File_Generic_MyParseProc(",
]:
    require(op_block, term, "rename operation block")

for stale in [
    "bug bug ParentOfTarget",
    "does not contain device path",
]:
    reject(pre_block, stale, "ParentOfTarget stale comment")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "### SREV-332: File Filter ParentOfTarget Context",
    "FILE_FLT_PARENT_TARGET_CONTEXT",
    "srev-332-file-flt-parent-target-context.schema.json",
    "Sandboxie/core/drv/file_flt.c",
    "ParentOfTarget",
    "RelatedFileObject",
    "File_Generic_MyParseProc",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-332 source gate passed")
