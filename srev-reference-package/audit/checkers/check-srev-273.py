#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-273 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-273 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-273-file-final-path-volume-name-owner.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-273 failed: schema is not draft-07")
if schema.get("id") != "FILE_FINAL_PATH_VOLUME_NAME_OWNER":
    raise SystemExit("SREV-273 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/dll/file.c":
    raise SystemExit("SREV-273 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "GetFinalPathNameByHandleW volume-name flags select the returned volume identity",
    "VOLUME_NAME_DOS returns a drive-letter path",
    "VOLUME_NAME_NT returns the NT device object path",
    "VOLUME_NAME_NONE returns a path with no drive information",
    "mounted-folder permanent-link matches use the target device identity for NT/NONE output",
    "mounted-folder permanent-link matches use the mounted-location drive identity plus mounted-folder suffix for DOS output",
    "SREV-143 owns permanent-link and GUID metadata correctness",
    "SREV-223 owns final-path returned-length handling",
    "SREV-271 owns FileNameInformation root-relative output",
    "this SREV changes comments and proof only",
]:
    require(contracts, term, "schema")

src = (ROOT / "Sandboxie/core/dll/file.c").read_text()
spec = (ROOT / "docs/plan/srev-273-file-final-path-volume-name-owner.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-273.md").read_text()

start = src.index("_FX WCHAR *File_GetFinalPathNameByHandleW_2")
end = src.index("// File_GetFinalPathNameByHandleW_3", start)
final_path = src[start:end]

for term in [
    "dwFlags &= VOLUME_NAME_GUID | VOLUME_NAME_NT | VOLUME_NAME_NONE;",
    "if (dwFlags & VOLUME_NAME_GUID)",
    "if (dwFlags & (VOLUME_NAME_NT | VOLUME_NAME_NONE))",
    "if (_wcsnicmp(TruePath, File_Mup, File_MupLen) == 0)",
    "VOLUME_NAME_GUID not supported for network shares",
    "return File_GetFinalPathNameByHandleW_3(TruePath, TruePath_len);",
    "file_link = File_FindPermLinksForMatchPath(TruePath, TruePath_len);",
    "SREV-273: GetFinalPathNameByHandleW volume-name flags choose the",
    "caller-visible volume identity.  Mounted-folder true paths use the",
    "target device for NT/NONE output and the mounted-location drive for",
    "DOS output.",
    "if (dwFlags != VOLUME_NAME_DOS)",
    "ReparsedPath = File_FixPermLinksForMatchPath(TruePath);",
    "suffix = TruePath + file_link->src_len;",
    "file_drive = File_GetDriveForPath(TruePath, TruePath_len);",
    "file_drive = File_GetDriveForPath(file_link->src, file_link->src_len);",
    "suffix = file_link->src + file_drive->len;",
    "suffix2 = TruePath + file_link->dst_len;",
    "if (dwFlags & VOLUME_NAME_NT)",
    "else if (dwFlags & VOLUME_NAME_NONE)",
    "else { // VOLUME_NAME_DOS",
]:
    require(final_path, term, "final-path source block")

for stale in [
    "if the volume is mounted on a directory then the TruePath here",
    "\\Device\\HarddiskVolume1\\MOUNT\\XXX  instead of",
    "\\Device\\HarddiskVolume2\\XXX",
    "to the form \\Device\\HarddiskVolume2\\XXX.  for DOS return",
]:
    reject(final_path, stale, "mounted-folder final-path comment")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for adjacent in [
    "docs/plan/srev-143-file-link-prefix-guid-translation.md",
    "docs/plan/srev-223-is-host-path-final-length.md",
    "docs/plan/srev-271-file-name-info-volume-relative-owner.md",
]:
    require(str((ROOT / adjacent).read_text()), "SREV-", adjacent)

for term in [
    "### SREV-273: File Final Path Volume-Name Owner",
    "FILE_FINAL_PATH_VOLUME_NAME_OWNER",
    "srev-273-file-final-path-volume-name-owner.schema.json",
    "Sandboxie/core/dll/file.c",
    "GetFinalPathNameByHandleW",
    "VOLUME_NAME_DOS",
    "mounted-folder",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-273 source gate passed")
