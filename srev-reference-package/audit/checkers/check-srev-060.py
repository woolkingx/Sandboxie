#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-060 failed: {label} missing {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-060-file-snapshot-relocation-copy-path.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-060 failed: schema is not draft-07")
if schema.get("id") != "FILE_SNAPSHOT_RELOCATION_COPY_PATH":
    raise SystemExit("SREV-060 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "File_GetName initializes output path pointers to NULL",
    "NT_SUCCESS(status) and CopyPath2 non-null proof",
    "must not continue with a stale previous CopyPath",
    "must not continue parent snapshot traversal",
]:
    require(contracts, term, "schema")

file_c = (ROOT / "Sandboxie/core/dll/file.c").read_text()
snap = (ROOT / "Sandboxie/core/dll/file_snapshots.c").read_text()
fdir = (ROOT / "Sandboxie/core/dll/file_dir.c").read_text()
spec = (ROOT / "docs/plan/srev-060-file-snapshot-relocation-copy-path.md").read_text()
ledger = read_combined_ledger(ROOT)

file_get_name_start = file_c.index("_FX NTSTATUS File_GetName(")
file_get_name_end = file_c.index("if (ObjectName == NO_RELOCATION)", file_get_name_start)
file_get_name_prefix = file_c[file_get_name_start:file_get_name_end]
for term in [
    "*OutTruePath = NULL;",
    "*OutCopyPath = NULL;",
]:
    require(file_get_name_prefix, term, "File_GetName local shape")

snap_start = snap.index("_FX ULONG File_GetPathFlagsEx(")
snap_end = snap.index("complete:", snap_start)
snap_func = snap[snap_start:snap_end]
for term in [
    "WCHAR* TruePath2 = NULL, *CopyPath2 = NULL;",
    "status = File_GetName(NULL, &objname, &TruePath2, &CopyPath2, NULL);",
    "if (NT_SUCCESS(status) && CopyPath2) {",
    "CopyPath = Dll_GetTlsNameBuffer(TlsData, COPY_NAME_BUFFER, (wcslen(CopyPath2) + 1) * sizeof(WCHAR));",
    "wcscpy((WCHAR*)CopyPath, CopyPath2);",
    "else\n\t\t\t\t\tCopyPath = NULL;",
]:
    require(snap_func, term, "file_snapshots relocation copy gate")

dir_start = fdir.index("if (File_Delete_v2) {", fdir.index("check if we have a relocation"))
dir_end = fdir.index("//\n\t// if there is no copy file", dir_start)
dir_block = fdir[dir_start:dir_end]
for term in [
    "WCHAR* TruePath2 = NULL, *CopyPath2 = NULL;",
    "status = File_GetName(NULL, &objname, &TruePath2, &CopyPath2, NULL);",
    "if (!NT_SUCCESS(status) || !CopyPath2)\n\t\t\t\t\t    break;",
    "CopyPath = Dll_GetTlsNameBuffer(TlsData, COPY_NAME_BUFFER, (wcslen(CopyPath2) + 1) * sizeof(WCHAR));",
    "wcscpy(CopyPath, CopyPath2);",
]:
    require(dir_block, term, "file_dir relocation copy gate")

for term in [
    "https://learn.microsoft.com/en-us/cpp/c-runtime-library/reference/strlen-wcslen-mbslen-mbslen-l-mbstrlen-mbstrlen-l?view=msvc-170",
    "https://learn.microsoft.com/en-us/cpp/c-runtime-library/reference/strcpy-s-wcscpy-s-mbscpy-s?view=msvc-170",
    "https://learn.microsoft.com/en-gb/windows-hardware/drivers/kernel/using-ntstatus-values",
    "srev-060-file-snapshot-relocation-copy-path.schema.json",
]:
    require(spec, term, "spec")

for term in [
    "### SREV-060: File Snapshot Relocation Copy Path Gate",
    "FILE_SNAPSHOT_RELOCATION_COPY_PATH",
    "srev-060-file-snapshot-relocation-copy-path.schema.json",
]:
    require(ledger, term, "ledger")

print("SREV-060 schema/source gate passed")
