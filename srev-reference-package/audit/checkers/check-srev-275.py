#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-275 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-275 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-275-file-rename-cross-volume-gate.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-275 failed: schema is not draft-07")
if schema.get("id") != "FILE_RENAME_CROSS_VOLUME_GATE":
    raise SystemExit("SREV-275 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/dll/file.c and Sandboxie/core/drv/file.c":
    raise SystemExit("SREV-275 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "File_Api_Rename owns Sandboxie driver-side API_RENAME_FILE projection of NT rename requests",
    "FILE_RENAME_INFORMATION is the concrete buffer for FileRenameInformation",
    "NT file rename is a same-volume operation",
    "STATUS_NOT_SAME_DEVICE is the legal NT result",
    "MoveFileEx with MOVEFILE_COPY_ALLOWED is the Win32 copy/delete fallback owner",
    "must preserve cross-volume failure rather than invent copy/delete policy",
    "sharing-violation retry in File_RenameFile remains unchanged",
    "this SREV changes comments and proof only",
]:
    require(contracts, term, "schema")

dll_src = (ROOT / "Sandboxie/core/dll/file.c").read_text()
drv_src = (ROOT / "Sandboxie/core/drv/file.c").read_text()
spec = (ROOT / "docs/plan/srev-275-file-rename-cross-volume-gate.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-275.md").read_text()

open_start = dll_src.index("_FX LONG File_RenameOpenFile(")
open_end = dll_src.index("// File_OpenForRenameFile", open_start)
open_block = dll_src[open_start:open_end]

rename_start = dll_src.index("_FX NTSTATUS File_RenameFile(")
rename_end = dll_src.index("// File_GetTrueHandle", rename_start)
rename_block = dll_src[rename_start:rename_end]

api_start = drv_src.index("_FX NTSTATUS File_Api_Rename(")
api_end = drv_src.index("// File_Api_GetName", api_start)
api_block = drv_src[api_start:api_end]

for term in [
    "FILE_RENAME_INFORMATION *info;",
    "info->RootDirectory = dir_handle;",
    "info->FileNameLength = name_len;",
    "status = __sys_NtSetInformationFile(",
    "info, info_len, FileRenameInformation);",
    "SREV-275: FILE_RENAME_INFORMATION is an NT same-volume rename.",
    "STATUS_NOT_SAME_DEVICE is the legal result for cross-volume targets;",
    "Win32 copy/delete fallback belongs above this hook.",
]:
    require(open_block, term, "rename-open-file block")

for term in [
    "LinkOp ? FileLinkInformation : FileRenameInformation",
    "status == STATUS_SHARING_VIOLATION && SourceHandle != FileHandle",
    "SourceHandle = FileHandle;",
    "SREV-275: FILE_RENAME_INFORMATION cannot move across volumes.",
    "Preserve STATUS_NOT_SAME_DEVICE so Win32 MoveFileEx callers with",
    "MOVEFILE_COPY_ALLOWED can decide whether to copy/delete instead.",
    "if (! NT_SUCCESS(status))",
    "__leave;",
]:
    require(rename_block, term, "rename-file block")

for term in [
    "FILE_RENAME_INFORMATION *info;",
    "info->RootDirectory = dir_handle;",
    "info->FileNameLength = name_len;",
    "status = ZwSetInformationFile(",
    "info, info_len, FileRenameInformation);",
    "SREV-275: FileRenameInformation is an NT same-volume rename.",
    "Preserve STATUS_NOT_SAME_DEVICE so callers that own copy/delete",
    "fallback can decide whether to move across volumes.",
]:
    require(api_block, term, "driver rename API block")

for stale in [
    "FIXME, we may get STATUS_NOT_SAME_DEVICE",
    "this API call is used to rename a file inside a folder",
    "rather than move files across folders",
    "which is smart enough",
]:
    reject(open_block, stale, "rename-open-file FIXME")
    reject(rename_block, stale, "rename-file FIXME")
    reject(api_block, stale, "driver rename API FIXME")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "### SREV-275: File Rename Cross-Volume Gate",
    "FILE_RENAME_CROSS_VOLUME_GATE",
    "srev-275-file-rename-cross-volume-gate.schema.json",
    "Sandboxie/core/dll/file.c",
    "Sandboxie/core/drv/file.c",
    "File_Api_Rename",
    "FILE_RENAME_INFORMATION",
    "STATUS_NOT_SAME_DEVICE",
    "MOVEFILE_COPY_ALLOWED",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-275 source gate passed")
