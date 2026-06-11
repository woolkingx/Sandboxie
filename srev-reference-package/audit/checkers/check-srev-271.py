#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-271 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-271 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-271-file-name-info-volume-relative-owner.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-271 failed: schema is not draft-07")
if schema.get("id") != "FILE_NAME_INFO_VOLUME_RELATIVE_OWNER":
    raise SystemExit("SREV-271 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/dll/file.c":
    raise SystemExit("SREV-271 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "File_NtQueryInformationFile owns the presentation shape",
    "root-relative to the caller-visible volume identity",
    "Mounted-folder matches from File_FindPermLinksForMatchPath",
    "File_GetGuidForPath finds a known volume identity",
    "SREV-143 still owns permanent-link and GUID metadata correctness",
]:
    require(contracts, term, "schema")

src = (ROOT / "Sandboxie/core/dll/file.c").read_text()
spec = (ROOT / "docs/plan/srev-271-file-name-info-volume-relative-owner.md").read_text()
srev_143 = (ROOT / "docs/plan/srev-143-file-link-prefix-guid-translation.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-271.md").read_text()

start = src.index("_FX NTSTATUS File_NtQueryInformationFile(")
end = src.index("// SbieDll_TranslateNtToDosPath", start)
query_info = src[start:end]

for term in [
    "else if (FileInformationClass != FileNameInformation)",
    "File_GetName(FileHandle, NULL, &TruePath, &CopyPath, NULL);",
    "file_link = File_FindPermLinksForMatchPath(TruePath, wcslen(TruePath));",
    "SREV-271: FileNameInformation returns a root-relative name.",
    "When a target volume is reached through a mounted folder",
    "mounted-folder destination prefix",
    "TruePath += file_link->dst_len;",
    "TruePathLen = wcslen(TruePath);",
    "LeaveCriticalSection(File_DrivesAndLinks_CritSec);",
    "if (SbieDll_TranslateNtToDosPath(TruePath))",
    "SREV-271: no DOS drive presentation exists for this NT path.",
    "If it matches a known volume GUID/device entry",
    "const FILE_GUID* guid = File_GetGuidForPath(TruePath, TruePathLen);",
    "TruePath += guid->len;",
    "TruePathLen -= guid->len;",
    "LeaveCriticalSection(File_DrivesAndLinks_CritSec);",
    "*(ULONG *)FileInformation = TruePathLen;",
    "memcpy((ULONG *)FileInformation + 1, TruePath, Length);",
]:
    require(query_info, term, "FileNameInformation source block")

for stale in [
    "without a drive letter, for example",
    "translates to \\\\Device\\\\HarddiskVolume1\\\\MOUNT",
    "else { // todo: fix-me this is not elegant",
]:
    reject(query_info, stale, "FileNameInformation comment")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "FILE_LINK_PREFIX_GUID_TRANSLATION",
    "File_FindPermLinksForMatchPath",
    "volume GUID path",
]:
    require(srev_143, term, "SREV-143 adjacency")

for term in [
    "### SREV-271: FileNameInformation Volume Relative Owner",
    "FILE_NAME_INFO_VOLUME_RELATIVE_OWNER",
    "srev-271-file-name-info-volume-relative-owner.schema.json",
    "Sandboxie/core/dll/file.c",
    "FileNameInformation",
    "SREV-143",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-271 source gate passed")
