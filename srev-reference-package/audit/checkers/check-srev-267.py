#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-267 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-267 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (
        ROOT
        / "docs/plan/srev-267-file-arm64ec-ntopenfile-bypass-comment-owner.schema.json"
    ).read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-267 failed: schema is not draft-07")
if schema.get("id") != "FILE_ARM64EC_NTOPENFILE_BYPASS_COMMENT_OWNER":
    raise SystemExit("SREV-267 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/dll/file.c":
    raise SystemExit("SREV-267 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "compatibility bypass not the normal Sandboxie file-policy route",
    "SREV-054 owns the executable half-open xtajit64.dll image range gate",
    "caller return address is inside the SREV-054 half-open xtajit64.dll image range",
    "Stale TODO or Fix-Me wording must not remain",
    "comments and proof only; behavior remains owned by SREV-054",
]:
    require(contracts, term, "schema")

src = (ROOT / "Sandboxie/core/dll/file.c").read_text()
spec = (
    ROOT / "docs/plan/srev-267-file-arm64ec-ntopenfile-bypass-comment-owner.md"
).read_text()
srev_054_spec = (ROOT / "docs/plan/srev-054-file-arm64ec-xtajit64-range.md").read_text()
srev_054_check = (ROOT / "docs/plan/check-srev-054.py").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-267.md").read_text()

start = src.index("_FX NTSTATUS File_NtOpenFile(")
end = src.index("// File_NtCreateFile", start)
ntopenfile = src[start:end]

for term in [
    "SREV-267: SREV-054 owns this ARM64EC compatibility bypass.",
    "xtajit64.dll is the caller",
    "normal File_NtCreateFileImpl route can",
    "hit __chkstk_arm64ec stack overflow",
    "only the SREV-054 half-open image",
    "range may use the direct NtOpenFile path.",
    "extern UINT_PTR Dll_xtajit64;",
    "extern UINT_PTR Dll_xtajit64_End;",
    "pRetAddr >= Dll_xtajit64 && pRetAddr < Dll_xtajit64_End",
    "status = __sys_NtOpenFile(",
]:
    require(ntopenfile, term, "File_NtOpenFile source")

for stale in [
    "TODO: Fix-Me",
    "To avoid this we call NtOpenFile directly",
]:
    reject(ntopenfile, stale, "File_NtOpenFile comment")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")
    require(srev_054_spec, term, "SREV-054 official reference inheritance")

for term in [
    "SREV-267",
    "TODO: Fix-Me",
    "File_NtOpenFile",
]:
    require(srev_054_check, term, "SREV-054 checker adjacency")

for term in [
    "### SREV-267: File ARM64EC NtOpenFile Bypass Comment Owner",
    "FILE_ARM64EC_NTOPENFILE_BYPASS_COMMENT_OWNER",
    "srev-267-file-arm64ec-ntopenfile-bypass-comment-owner.schema.json",
    "Sandboxie/core/dll/file.c",
    "SREV-054",
    "File_NtOpenFile",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-267 source gate passed")
