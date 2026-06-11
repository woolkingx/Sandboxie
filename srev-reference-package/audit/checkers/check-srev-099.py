#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-099 failed: {label} missing {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-099-flt-copied-abi-comment-contract.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-099 failed: schema is not draft-07")
if schema.get("id") != "FLT_COPIED_ABI_COMMENT_CONTRACT":
    raise SystemExit("SREV-099 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "local copied fltKernel.h subset",
    "_WIN32_WINNT below Vista / XP driver build compatibility",
    "does not change the copied FLT ABI layout or numeric constants",
    "FileSystemControl and DeviceIoControl union arms",
    "Common, Neither, Buffered, and Direct",
    "Common, Neither, Buffered, Direct, and FastIo",
    "ULONG partitioned into name format bits, query method bits, unused bits, and flags",
    "FLT_FILE_NAME_NORMALIZED and FLT_FILE_NAME_QUERY_DEFAULT",
    "must not describe official partitioned ABI fields as broken",
    "file_flt.c remains the local Filter Manager consumer",
]:
    require(contracts, term, "schema")

my_flt = (ROOT / "Sandboxie/core/drv/my_fltkernel.h").read_text()
file_flt = (ROOT / "Sandboxie/core/drv/file_flt.c").read_text()
process = (ROOT / "Sandboxie/core/drv/process.c").read_text()
spec = (ROOT / "docs/plan/srev-099-flt-copied-abi-comment-contract.md").read_text()
ledger = read_combined_ledger(ROOT)

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "We can't use fltKernel.h from the DDK",
    "_WIN32_WINNT < NTDDI_VISTA",
    "driver that will run under XP",
    "typedef union _FLT_PARAMETERS",
    "} FileSystemControl;",
    "} DeviceIoControl;",
    "The parameters are split into 3 separate unions based on the",
    "method of the FSCTL",
    "method of the IOCTL",
    "Common;",
    "Neither;",
    "Buffered;",
    "Direct;",
    "FastIo;",
    "The FLT_FILE_NAME_OPTIONS is a ULONG partitioned into three",
    "typedef ULONG FLT_FILE_NAME_OPTIONS;",
    "#define FLT_VALID_FILE_NAME_FORMATS 0x000000ff",
    "#define FLT_FILE_NAME_NORMALIZED    0x01",
    "#define FLT_FILE_NAME_OPENED        0x02",
    "#define FLT_FILE_NAME_SHORT         0x03",
    "#define FLT_VALID_FILE_NAME_QUERY_METHODS 0x0000ff00",
    "#define FLT_FILE_NAME_QUERY_DEFAULT     0x0100",
    "#define FLT_FILE_NAME_QUERY_CACHE_ONLY  0x0200",
    "#define FLT_FILE_NAME_QUERY_FILESYSTEM_ONLY 0x0300",
    "#define FLT_FILE_NAME_QUERY_ALWAYS_ALLOW_CACHE_LOOKUP 0x0400",
    "#define FLT_VALID_FILE_NAME_FLAGS 0xff000000",
]:
    require(my_flt, term, "my_fltkernel.h copied ABI shape")

for stale in [
    "broken out into",
    "broken down into",
]:
    if stale in my_flt:
        raise SystemExit(f"SREV-099 failed: stale wording remains {stale!r}")

for term in [
    "#include \"my_fltkernel.h\"",
    "FltGetFileNameInformation(Data, FLT_FILE_NAME_NORMALIZED | FLT_FILE_NAME_QUERY_DEFAULT",
    "Iopb->Parameters.Create.SecurityContext",
    "Iopb->Parameters.SetFileInformation.FileInformationClass",
    "Parms = &Iopb->Parameters;",
]:
    require(file_flt, term, "file_flt.c consumer shape")

for term in [
    "FltGetFileNameInformationUnsafe(CreateInfo->FileObject, NULL, FLT_FILE_NAME_NORMALIZED | FLT_FILE_NAME_QUERY_DEFAULT",
    "PFLT_FILE_NAME_INFORMATION nameInfo",
]:
    require(process, term, "process.c unsafe name-query consumer shape")

for term in [
    "FLT_PARAMETERS",
    "FileSystemControl",
    "DeviceIoControl",
    "FLT_FILE_NAME_OPTIONS",
    "bits 0..7",
    "bits 8..15",
    "bits 16..23",
    "bits 24..31",
    "No ABI layout, numeric constant, callback registration, or runtime behavior was",
]:
    require(spec, term, "spec shape")

for term in [
    "### SREV-099: FLT Copied ABI Comment Contract",
    "FLT_COPIED_ABI_COMMENT_CONTRACT",
    "srev-099-flt-copied-abi-comment-contract.schema.json",
]:
    require(ledger, term, "ledger")

print("SREV-099 schema/source gate passed")
