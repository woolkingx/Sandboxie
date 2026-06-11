#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-265 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-265 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-265-file-altboxpath-allocation-publication-gate.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-265 failed: schema is not draft-07")
if schema.get("id") != "FILE_ALTBOXPATH_ALLOCATION_PUBLICATION_GATE":
    raise SystemExit("SREV-265 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/dll/file_init.c":
    raise SystemExit("SREV-265 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "Dll_GetTlsNameBuffer output must be checked before wmemcpy",
    "copied into a local allocation before File_AltBoxPath is published",
    "File_AltBoxPathLen is published only after",
    "does not change mount-point conversion semantics",
]:
    require(contracts, term, "schema")

file_init = (ROOT / "Sandboxie/core/dll/file_init.c").read_text()
srev_196 = (ROOT / "docs/plan/srev-196-dll-tls-name-buffer-allocation-contract.md").read_text()
srev_196_check = (ROOT / "docs/plan/check-srev-196.py").read_text()
srev_264 = (ROOT / "docs/plan/srev-264-file-altboxpath-legacy-prefix-owner.md").read_text()
srev_264_check = (ROOT / "docs/plan/check-srev-264.py").read_text()
spec = (ROOT / "docs/plan/srev-265-file-altboxpath-allocation-publication-gate.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-265.md").read_text()

start = file_init.index("the sandbox path may be specified on a directory mount point")
end = file_init.index("//---------------------------------------------------------------------------\n// File_AdjustDrives", start)
block = file_init[start:end]

for term in [
    "WCHAR *TruePath = Dll_GetTlsNameBuffer(TlsData, TRUE_NAME_BUFFER,",
    "if (TruePath) {\n            wmemcpy(TruePath, Dll_BoxFilePath, Dll_BoxFilePathLen + 1);",
    "BOOLEAN converted =\n                File_GetName_ConvertLinks(TlsData, &TruePath, FALSE);",
    "WCHAR *AltBoxPath = Dll_Alloc((len + 1) * sizeof(WCHAR));",
    "if (AltBoxPath) {\n                    wmemcpy(AltBoxPath, TruePath, len + 1);",
    "File_AltBoxPath = AltBoxPath;",
    "File_AltBoxPathLen = len;",
]:
    require(block, term, "file_init mount-point gate")

if not block.index("if (TruePath)") < block.index("wmemcpy(TruePath, Dll_BoxFilePath, Dll_BoxFilePathLen + 1);"):
    raise SystemExit("SREV-265 failed: TruePath copy precedes null gate")
if not block.index("WCHAR *AltBoxPath = Dll_Alloc") < block.index("File_AltBoxPath = AltBoxPath;"):
    raise SystemExit("SREV-265 failed: File_AltBoxPath publish precedes local allocation")
if not block.index("if (AltBoxPath)") < block.index("File_AltBoxPathLen = len;"):
    raise SystemExit("SREV-265 failed: File_AltBoxPathLen publish precedes allocation gate")

reject(
    block,
    "WCHAR *TruePath = Dll_GetTlsNameBuffer(TlsData, TRUE_NAME_BUFFER,\n                                (Dll_BoxFilePathLen + 1) * sizeof(WCHAR));\n        wmemcpy(TruePath, Dll_BoxFilePath, Dll_BoxFilePathLen + 1);",
    "file_init pre-gate TruePath copy",
)
reject(block, "File_AltBoxPath = Dll_Alloc((len + 1) * sizeof(WCHAR));", "file_init direct global allocation")
reject(block, "wmemcpy(File_AltBoxPath, TruePath, len + 1);", "file_init global copy before allocation gate")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "SREV-265 records one caller-side consequence",
    "must check the returned TLS name buffer before",
]:
    require(srev_196, term, "SREV-196 spec adjacency")
for term in [
    "if (TruePath) {\\n            wmemcpy(TruePath, Dll_BoxFilePath, Dll_BoxFilePathLen + 1);",
    "WCHAR *AltBoxPath = Dll_Alloc((len + 1) * sizeof(WCHAR));",
    "SREV-265",
]:
    require(srev_196_check, term, "SREV-196 checker adjacency")

for term in [
    "SREV-265 later added the allocation/publication gate",
    "published only after the dedicated allocation succeeds",
]:
    require(srev_264, term, "SREV-264 spec adjacency")
for term in [
    "if (TruePath) {\\n            wmemcpy(TruePath, Dll_BoxFilePath, Dll_BoxFilePathLen + 1);",
    "WCHAR *AltBoxPath = Dll_Alloc((len + 1) * sizeof(WCHAR));",
    "SREV-265 later added the allocation/publication gate",
]:
    require(srev_264_check, term, "SREV-264 checker adjacency")

for term in [
    "### SREV-265: File AltBoxPath Allocation Publication Gate",
    "FILE_ALTBOXPATH_ALLOCATION_PUBLICATION_GATE",
    "srev-265-file-altboxpath-allocation-publication-gate.schema.json",
    "Sandboxie/core/dll/file_init.c",
    "Dll_GetTlsNameBuffer",
    "File_AltBoxPath",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-265 source gate passed")
