#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-143 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-143 failed: {label} still contains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-143-file-link-prefix-guid-translation.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-143 failed: schema is not draft-07")
if schema.get("id") != "FILE_LINK_PREFIX_GUID_TRANSLATION":
    raise SystemExit("SREV-143 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "file_link.c owns permanent-link prefix matching and volume GUID path translation inside the DLL path metadata lock",
    "A permanent link source match is valid only when PathLen >= src_len, the prefix bytes match, and the character at Path[src_len] is either a backslash or NUL",
    "Path[PathLen] is the end of the caller-supplied string when PathLen comes from wcslen(path), so it cannot prove the prefix boundary",
    "Known volume GUID targets in \\\\??\\\\Volume{GUID}\\\\ form must return the allocated File_ConcatPath2 result to the caller",
    "The GUID lookup lock is released exactly once after a successful File_GetLinkForGuid lookup",
    "File_ConcatPath2 remains the owner-local path allocation helper and returns a NUL-terminated allocated string",
    "Symlink and reparse target byte offsets remain interpreted as counted REPARSE_DATA_BUFFER data",
]:
    require(contracts, term, "schema")

file_link = (ROOT / "Sandboxie/core/dll/file_link.c").read_text()
file_init = (ROOT / "Sandboxie/core/dll/file_init.c").read_text()
file_misc = (ROOT / "Sandboxie/core/dll/file_misc.c").read_text()
spec = (ROOT / "docs/plan/srev-143-file-link-prefix-guid-translation.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-143.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "struct _FILE_LINK",
    "struct _FILE_GUID",
    "static LIST *File_PermLinks = NULL;",
    "static LIST *File_GuidLinks = NULL;",
    "static CRITICAL_SECTION *File_DrivesAndLinks_CritSec = NULL;",
]:
    require(file_link, term, "file link data owner")

guid_start = file_link.index("_FX WCHAR* File_TranslateGuidToNtPath2")
guid_end = file_link.index("//---------------------------------------------------------------------------\n// File_TranslateGuidToNtPath", guid_start)
guid_func = file_link[guid_start:guid_end]
for term in [
    "WCHAR* NtPath = NULL;",
    "GuidPath && GuidPathLen >= 48",
    "_wcsnicmp(GuidPath, L\"\\\\??\\\\Volume{\", 11) == 0",
    "FILE_GUID* guid = File_GetLinkForGuid(&GuidPath[10]);",
    "NtPath = File_ConcatPath2(guid->path, guid->len, GuidPath + 48, GuidPathLen - 48);",
    "LeaveCriticalSection(File_DrivesAndLinks_CritSec);",
    "return NtPath;",
]:
    require(guid_func, term, "GUID translation")
reject(
    guid_func,
    "\n            File_ConcatPath2(guid->path, guid->len, GuidPath + 48, GuidPathLen - 48);\n",
    "discarded GUID translation allocation",
)

for term in [
    "_FX WCHAR *File_ConcatPath2(const WCHAR *Path1, ULONG Path1Len, const WCHAR *Path2, ULONG Path2Len)",
    "WCHAR* Path = Dll_Alloc((Length + 1) * sizeof(WCHAR));",
    "wmemcpy(Path, Path1, Path1Len);",
    "wmemcpy(Path + Path1Len, Path2, Path2Len);",
    "Path[Length] = L'\\0';",
    "return Path;",
]:
    require(file_init, term, "File_ConcatPath2 allocation helper")

drive_link_start = file_link.index("_FX const FILE_DRIVE *File_GetDriveAndLinkForPath")
drive_link_end = file_link.index("//---------------------------------------------------------------------------\n// File_FindPermLinksForMatchPath", drive_link_start)
drive_link_func = file_link[drive_link_start:drive_link_end]
for term in [
    "EnterCriticalSection(File_DrivesAndLinks_CritSec);",
    "const ULONG src_len = link->src_len;",
    "PathLen >= src_len",
    "(Path[src_len] == L'\\\\' || Path[src_len] == L'\\0')",
    "_wcsnicmp(Path, link->src, src_len) == 0",
    "*OutLink = link;",
    "drive = File_GetDriveForPath(Path, PathLen);",
    "// on exit, File_DrivesAndLinks_CritSec is locked just once",
]:
    require(drive_link_func, term, "permanent-link prefix boundary")
reject(drive_link_func, "Path[PathLen] == L'\\\\'", "stale whole-string boundary")
reject(drive_link_func, "Path[PathLen] == L'\\0'", "stale whole-string boundary")

for term in [
    "const WCHAR *ptr = Path + drive->len;",
    "if (*ptr == L'\\\\' || *ptr == L'\\0')",
    "(name[src_len] == L'\\\\' || name[src_len] == L'\\0')",
    "(name[dst_len] == L'\\\\' || name[dst_len] == L'\\0')",
]:
    require(file_link, term, "local prefix-boundary precedent")

for term in [
    "File_GetDriveAndLinkForPath(path, wcslen(path), FileLink);",
    "File_TranslateGuidToNtPath2(SubstituteNameBuffer, SubstituteNameLength / sizeof(WCHAR));",
    "REPARSE_DATA_BUFFER* reparseDataBuffer =",
    "SubstituteNameOffset/sizeof(WCHAR)",
    "SubstituteNameLength / sizeof(WCHAR)",
]:
    if term.startswith("File_GetDriveAndLinkForPath"):
        require(file_misc, term, "wcslen call site")
    else:
        require(file_link, term, "adjacent GUID/reparse flow")

for term in [
    "Sandboxie/core/dll/file_link.c",
    "Sandboxie/core/dll/file_init.c",
    "Sandboxie/core/dll/file_misc.c",
    "### SREV-143: File Link Prefix And GUID Translation",
    "FILE_LINK_PREFIX_GUID_TRANSLATION",
    "srev-143-file-link-prefix-guid-translation.schema.json",
    "Path[src_len]",
    "NtPath = File_ConcatPath2",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-143 schema/source gate passed")
