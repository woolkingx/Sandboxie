#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-125 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-125 failed: {label} still contains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-125-file-copy-junction-handle-state.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-125 failed: schema is not draft-07")
if schema.get("id") != "FILE_COPY_JUNCTION_HANDLE_STATE":
    raise SystemExit("SREV-125 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "File_MigrateJunction opens the source reparse point before querying source metadata or reparse data",
    "FILE_NETWORK_OPEN_INFORMATION is used only after NtQueryInformationFile FileNetworkOpenInformation succeeds",
    "source reparse data is used only after FSCTL_GET_REPARSE_POINT succeeds",
    "every local failure after TrueHandle opens closes TrueHandle before returning",
    "destination reparse data is set only after destination NtCreateFile succeeds and initializes CopyHandle",
    "destination create failure frees copied security descriptor storage when one exists and returns before FSCTL_SET_REPARSE_POINT",
    "reparse data shape ACL copy policy destination create options and attribute-copy behavior are unchanged",
]:
    require(contracts, term, "schema")

source = (ROOT / "Sandboxie/core/dll/file_copy.c").read_text()
spec = (ROOT / "docs/plan/srev-125-file-copy-junction-handle-state.md").read_text()
ledger = read_combined_ledger(ROOT)

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

junction = source[
    source.index("_FX NTSTATUS File_MigrateJunction"):
]

query_gate = """status = __sys_NtQueryInformationFile(
        TrueHandle, &IoStatusBlock, &open_info,
        sizeof(FILE_NETWORK_OPEN_INFORMATION), FileNetworkOpenInformation);

    if (!NT_SUCCESS(status)) {
        NtClose(TrueHandle);
        return status;
    }

    //
    // Get the reparse point data from the source"""
require(junction, query_gate, "source metadata query gate")

get_gate = """status = __sys_NtFsControlFile(TrueHandle, NULL, NULL, NULL, &IoStatusBlock, FSCTL_GET_REPARSE_POINT, NULL, 0, reparseDataBuffer, MAXIMUM_REPARSE_DATA_BUFFER_SIZE);

    if (!NT_SUCCESS(status)) {
        NtClose(TrueHandle);
        return status;
    }"""
require(junction, get_gate, "source reparse get gate")

create_gate = """if (!NT_SUCCESS(status)) {
        NtClose(TrueHandle);
        if (pSecurityDescriptor)
            Dll_Free(pSecurityDescriptor);
        return status;
    }

    //
    // Set the reparse point data to the destination"""
require(junction, create_gate, "destination create gate")

if junction.index("NtQueryInformationFile") > junction.index("FSCTL_GET_REPARSE_POINT"):
    raise SystemExit("SREV-125 failed: source metadata query is after reparse get")
if junction.index("if (!NT_SUCCESS(status)) {\n        NtClose(TrueHandle);\n        return status;\n    }\n\n    //\n    // Get the reparse point data") > junction.index("FSCTL_GET_REPARSE_POINT"):
    raise SystemExit("SREV-125 failed: source metadata failure gate is after reparse get")
if junction.index("return status;\n    }\n\n    //\n    // Set the reparse point data to the destination") > junction.index("FSCTL_SET_REPARSE_POINT"):
    raise SystemExit("SREV-125 failed: destination create failure return is after set reparse")

reject(junction, """status = __sys_NtFsControlFile(TrueHandle, NULL, NULL, NULL, &IoStatusBlock, FSCTL_GET_REPARSE_POINT, NULL, 0, reparseDataBuffer, MAXIMUM_REPARSE_DATA_BUFFER_SIZE);

    if (!NT_SUCCESS(status))
        return status;""", "source reparse failure handle leak")
reject(junction, """if (!NT_SUCCESS(status)) {
        NtClose(TrueHandle);
        if (pSecurityDescriptor)
            Dll_Free(pSecurityDescriptor);
    }

    //
    // Set the reparse point data to the destination""", "destination create fallthrough")

for term in [
    "FILE_OPEN_REPARSE_POINT | FILE_SYNCHRONOUS_IO_NONALERT",
    "REPARSE_DATA_BUFFER* reparseDataBuffer = (REPARSE_DATA_BUFFER*)buf;",
    "FSCTL_GET_REPARSE_POINT",
    "FILE_SYNCHRONOUS_IO_NONALERT | FILE_DIRECTORY_FILE | FILE_OPEN_REPARSE_POINT",
    "FSCTL_SET_REPARSE_POINT",
    "REPARSE_MOUNTPOINT_HEADER_SIZE + reparseDataBuffer->ReparseDataLength",
    "File_SetAttributes(CopyHandle, CopyPath, &info);",
    "NtClose(CopyHandle);",
]:
    require(junction, term, "preserved junction path")

for term in [
    "### SREV-125: File Copy Junction Handle State",
    "FILE_COPY_JUNCTION_HANDLE_STATE",
    "srev-125-file-copy-junction-handle-state.schema.json",
    "Sandboxie/core/dll/file_copy.c",
    "File_MigrateJunction",
    "TrueHandle",
    "CopyHandle",
    "NtQueryInformationFile",
    "FSCTL_GET_REPARSE_POINT",
    "FSCTL_SET_REPARSE_POINT",
]:
    require(ledger, term, "ledger")

print("SREV-125 schema/source gate passed")
