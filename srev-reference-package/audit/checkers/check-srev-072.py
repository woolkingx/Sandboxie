#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-072 failed: {label} missing {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-072-file-recovery-mup-path-buffer.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-072 failed: schema is not draft-07")
if schema.get("id") != "FILE_RECOVERY_MUP_PATH_BUFFER":
    raise SystemExit("SREV-072 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "wmemcpy requires valid source and destination buffers",
    "path2 may receive the File_Mup prefix only after Dll_Alloc returns non-null",
    "path2 may receive the redirector suffix only inside the same allocation-success gate",
    "TruePath may be replaced by path2 only after both wide-copy operations",
    "Allocation failure must keep the original TruePath",
]:
    require(contracts, term, "schema")

src = (ROOT / "Sandboxie/core/dll/file_recovery.c").read_text()
spec = (ROOT / "docs/plan/srev-072-file-recovery-mup-path-buffer.md").read_text()
ledger = read_combined_ledger(ROOT)

start = src.index("_FX BOOLEAN File_IsRecoverable(")
end = src.index("// File_RecordRecover", start)
func = src[start:end]

for term in [
    "WCHAR *path2 = Dll_Alloc(len2);\n            if (path2) {\n                wmemcpy(path2, File_Mup, File_MupLen);",
    "wmemcpy(path2 + File_MupLen, ptr + 1, len1 + 1);",
    "TruePath = (const WCHAR *)path2;",
]:
    require(func, term, "File_IsRecoverable source")

if func.index("if (path2)") > func.index("wmemcpy(path2, File_Mup, File_MupLen);"):
    raise SystemExit("SREV-072 failed: path2 gate appears after prefix copy")
if func.index("wmemcpy(path2 + File_MupLen") > func.index("TruePath = (const WCHAR *)path2;"):
    raise SystemExit("SREV-072 failed: TruePath assignment appears before suffix copy")
if "WCHAR *path2 = Dll_Alloc(len2);\n            wmemcpy(path2" in func:
    raise SystemExit("SREV-072 failed: stale ungated path2 copy remains")

for term in [
    "https://learn.microsoft.com/en-us/cpp/c-runtime-library/reference/memcpy-wmemcpy?view=msvc-170",
    "srev-072-file-recovery-mup-path-buffer.schema.json",
]:
    require(spec, term, "spec")

for term in [
    "### SREV-072: File Recovery MUP Path Buffer",
    "FILE_RECOVERY_MUP_PATH_BUFFER",
    "srev-072-file-recovery-mup-path-buffer.schema.json",
]:
    require(ledger, term, "ledger")

print("SREV-072 schema/source gate passed")
