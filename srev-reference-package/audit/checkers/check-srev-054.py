#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-054 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-054 failed: {label} still contains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-054-file-arm64ec-xtajit64-range.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-054 failed: schema is not draft-07")
if schema.get("id") != "FILE_ARM64EC_XTAJIT64_RANGE_GATE":
    raise SystemExit("SREV-054 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "GetModuleHandleW returns a handle",
    "PE SizeOfImage field owns the in-memory image extent",
    "half-open xtajit64.dll image range",
    "zero or invalid xtajit64.dll base/end disables the bypass",
    "must not use a hard-coded image-size constant",
]:
    require(contracts, term, "schema")

file_src = (ROOT / "Sandboxie/core/dll/file.c").read_text()
dllmain_src = (ROOT / "Sandboxie/core/dll/dllmain.c").read_text()
spec = (ROOT / "docs/plan/srev-054-file-arm64ec-xtajit64-range.md").read_text()
ledger = read_combined_ledger(ROOT)
srev_267 = (
    ROOT / "docs/plan/srev-267-file-arm64ec-ntopenfile-bypass-comment-owner.md"
).read_text()

file_start = file_src.index("_FX NTSTATUS File_NtOpenFile(")
file_end = file_src.index("// File_NtCreateFile", file_start)
ntopenfile = file_src[file_start:file_end]

for term in [
    "UINT_PTR Dll_xtajit64 = 0;",
    "UINT_PTR Dll_xtajit64_End = 0;",
    "Dll_xtajit64 = (UINT_PTR)GetModuleHandle(L\"xtajit64.dll\");",
    "PIMAGE_DOS_HEADER dosHeader = (PIMAGE_DOS_HEADER)Dll_xtajit64;",
    "dosHeader->e_magic == IMAGE_DOS_SIGNATURE",
    "PIMAGE_NT_HEADERS64 ntHeader =",
    "ntHeader->Signature == IMAGE_NT_SIGNATURE",
    "ntHeader->OptionalHeader.SizeOfImage",
    "Dll_xtajit64 + ntHeader->OptionalHeader.SizeOfImage > Dll_xtajit64",
    "Dll_xtajit64_End = Dll_xtajit64 + ntHeader->OptionalHeader.SizeOfImage;",
]:
    require(dllmain_src, term, "dllmain source")

for term in [
    "extern UINT_PTR Dll_xtajit64;",
    "extern UINT_PTR Dll_xtajit64_End;",
    "if (Dll_xtajit64 && Dll_xtajit64_End &&",
    "pRetAddr >= Dll_xtajit64 && pRetAddr < Dll_xtajit64_End)",
    "status = __sys_NtOpenFile(",
]:
    require(ntopenfile, term, "file source")

for term in [
    "SREV-267: SREV-054 owns this ARM64EC compatibility bypass.",
    "only the SREV-054 half-open image",
]:
    require(ntopenfile, term, "File_NtOpenFile SREV-267 adjacency")

reject(file_src, "Dll_xtajit64 + 0x180000", "file source")
reject(dllmain_src, "void* Dll_xtajit64 = NULL;", "dllmain source")
reject(ntopenfile, "TODO: Fix-Me", "File_NtOpenFile comment")

for term in [
    "https://learn.microsoft.com/en-us/windows/win32/api/libloaderapi/nf-libloaderapi-getmodulehandlew",
    "https://learn.microsoft.com/en-us/windows/win32/debug/pe-format",
    "srev-054-file-arm64ec-xtajit64-range.schema.json",
    "SREV-267 later removed the stale `TODO: Fix-Me` wording",
]:
    require(spec, term, "spec")

for term in [
    "FILE_ARM64EC_NTOPENFILE_BYPASS_COMMENT_OWNER",
    "SREV-054 owns the executable range gate",
    "stale `TODO` / `Fix-Me` wording must not remain",
]:
    require(srev_267, term, "SREV-267 adjacency")

for term in [
    "### SREV-054: ARM64EC NtOpenFile xtajit64 Range Gate",
    "FILE_ARM64EC_XTAJIT64_RANGE_GATE",
    "srev-054-file-arm64ec-xtajit64-range.schema.json",
    "SREV-267",
]:
    require(ledger, term, "ledger")

print("SREV-054 schema/source gate passed")
