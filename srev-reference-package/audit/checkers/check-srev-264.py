#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-264 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-264 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-264-file-altboxpath-legacy-prefix-owner.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-264 failed: schema is not draft-07")
if schema.get("id") != "FILE_ALTBOXPATH_LEGACY_PREFIX_OWNER":
    raise SystemExit("SREV-264 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/dll/file.c":
    raise SystemExit("SREV-264 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "File_FindBoxPrefix owns the ordered box-root prefix set",
    "File_AltBoxPath is a legacy mount-point prefix fallback",
    "Removal requires Windows proof",
    "does not change prefix order matching semantics",
]:
    require(contracts, term, "schema")

file_src = (ROOT / "Sandboxie/core/dll/file.c").read_text()
file_init = (ROOT / "Sandboxie/core/dll/file_init.c").read_text()
srev_057 = (ROOT / "docs/plan/srev-057-file-init-box-root-path.md").read_text()
srev_057_check = (ROOT / "docs/plan/check-srev-057.py").read_text()
spec = (ROOT / "docs/plan/srev-264-file-altboxpath-legacy-prefix-owner.md").read_text()
srev_264 = spec
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-264.md").read_text()

start = file_src.index("_FX ULONG File_FindBoxPrefix")
end = file_src.index("_FX NTSTATUS File_GetCopyPathImpl", start)
func = file_src[start:end]

for term in [
    "SREV-264: File_AltBoxPath is a legacy mount-point prefix fallback.",
    "Removal must first reprove the SREV-057 raw-root/mount-point matrix.",
    "Dll_BoxFilePath, Dll_BoxFilePathLen,",
    "Dll_BoxFileRawPath, Dll_BoxFileRawPathLen,",
    "File_AltBoxPath, File_AltBoxPathLen",
]:
    require(func, term, "File_FindBoxPrefix")

reject(func, "ToDo: deprecated, remove - raw path is more reliable and covers all cases", "File_FindBoxPrefix")

for term in [
    "the sandbox path may be specified on a directory mount point",
    "keep the mount point location",
    "if (TruePath) {\n            wmemcpy(TruePath, Dll_BoxFilePath, Dll_BoxFilePathLen + 1);",
    "File_GetName_ConvertLinks(TlsData, &TruePath, FALSE);",
    "WCHAR *AltBoxPath = Dll_Alloc((len + 1) * sizeof(WCHAR));",
    "if (AltBoxPath) {",
    "File_AltBoxPath = AltBoxPath;",
    "File_AltBoxPathLen = len;",
]:
    require(file_init, term, "file_init mount-point publication")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "SREV-264 later classified `File_AltBoxPath`",
    "raw-root/mount-point matrix",
    "File_AltBoxPath` legacy-fallback adjacency",
]:
    require(srev_057, term, "SREV-057 spec adjacency")

for term in [
    "SREV-265 later added the allocation/publication gate",
    "published only after the dedicated allocation succeeds",
]:
    require(srev_264, term, "SREV-264 spec adjacency")

for term in [
    "SREV-264: File_AltBoxPath is a legacy mount-point prefix fallback.",
    "Removal must first reprove the SREV-057 raw-root/mount-point matrix.",
    "ToDo: deprecated, remove - raw path is more reliable and covers all cases",
    "SREV-264",
]:
    require(srev_057_check, term, "SREV-057 checker adjacency")

for term in [
    "### SREV-264: File AltBoxPath Legacy Prefix Owner",
    "FILE_ALTBOXPATH_LEGACY_PREFIX_OWNER",
    "srev-264-file-altboxpath-legacy-prefix-owner.schema.json",
    "Sandboxie/core/dll/file.c",
    "File_FindBoxPrefix",
    "SREV-057",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-264 source gate passed")
