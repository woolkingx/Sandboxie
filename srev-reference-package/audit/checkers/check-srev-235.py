#!/usr/bin/env python3
import json
from pathlib import Path

from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-235 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-235 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-235-gdi-header-bitmapbits-signature.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-235 failed: schema is not draft-07")
if schema.get("id") != "GDI_HEADER_BITMAPBITS_SIGNATURE_CONTRACT":
    raise SystemExit("SREV-235 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/dll/gdi.h":
    raise SystemExit("SREV-235 failed: wrong owner")

official_refs = "\n".join(schema["official_references"])
for term in [
    "nf-wingdi-getenhmetafilebits",
    "nf-wingdi-getbitmapbits",
    "nf-wingdi-deleteobject",
    "nf-wingdi-deleteenhmetafile",
]:
    require(official_refs, term, "official reference")

contracts = "\n".join(schema["contracts"])
for term in [
    "GDI function-pointer declarations",
    "P_GetBitmapBits must match",
    "LONG HBITMAP LONG LPVOID",
    "zero-size null-buffer query",
    "Linux source proof is not Windows",
]:
    require(contracts, term, "schema contract")

spec = (ROOT / "docs/plan/srev-235-gdi-header-bitmapbits-signature.md").read_text()
header = (ROOT / "Sandboxie/core/dll/gdi.h").read_text()
gdi = (ROOT / "Sandboxie/core/dll/gdi.c").read_text()
ole = (ROOT / "Sandboxie/core/dll/ole.cpp").read_text()
ledger = read_combined_ledger(ROOT)
fragment = (ROOT / "docs/plan/ledger/srev-235.md").read_text()

for term in [
    "typedef UINT (*P_GetEnhMetaFileBits)(",
    "HENHMETAFILE hemf,",
    "UINT cbBuffer,",
    "LPBYTE lpbBuffer",
    "typedef LONG (*P_GetBitmapBits)(",
    "HBITMAP hBitmap,",
    "LONG cbBuffer,",
    "LPVOID lpvBits",
    "typedef BOOL (*P_DeleteObject)(",
    "HGDIOBJ hObject);",
    "typedef BOOL (*P_DeleteEnhMetaFile)(",
    "HENHMETAFILE hemf );",
    "extern P_GetBitmapBits              __sys_GetBitmapBits;",
]:
    require(header, term, "header signature")

reject(header, "typedef UINT (*P_GetBitmapBits)(", "old unsigned GetBitmapBits return")
bitmap_start = header.index("typedef LONG (*P_GetBitmapBits)(")
bitmap_end = header.index("typedef BOOL (*P_DeleteObject)(", bitmap_start)
bitmap_typedef = header[bitmap_start:bitmap_end]
reject(bitmap_typedef, "UINT cbBuffer", "old unsigned GetBitmapBits size")
reject(bitmap_typedef, "LPBYTE lpbBuffer", "old byte pointer GetBitmapBits buffer")

for term in [
    "P_GetBitmapBits                 __sys_GetBitmapBits                 = NULL;",
    "__sys_GetBitmapBits = (P_GetBitmapBits)",
    "GetProcAddress(module, \"GetBitmapBits\");",
]:
    require(gdi, term, "gdi.c resolution topology")

for term in [
    "#include \"gdi.h\"",
    "(__sys_GetBitmapBits != 0 && 0 != __sys_GetBitmapBits(pmedium->hBitmap, 0, NULL))",
    "__sys_DeleteObject(pmedium->hBitmap);",
    "pmedium->tymed = TYMED_NULL;",
]:
    require(ole, term, "ole.cpp release topology")

for term in [
    "SREV-061: GDI Printer Retry Device Name Boundary",
    "owner: Sandboxie/core/dll/gdi.c",
    "SREV-087: Win32k Electron Workaround Boundary",
    "ProcessSystemCallDisablePolicy",
]:
    require(ledger, term, "existing GDI owner coverage")

for term in [
    "GetBitmapBits(HBITMAP hbit, LONG cb, LPVOID lpvBits) -> LONG",
    "No `GetProcAddress` topology",
    "old typedef used the right argument count",
    "patched-source-level-after-official-gdi-signature-review",
]:
    require(spec + "\n" + fragment, term, "spec or ledger classification")

for term in [
    "kind: srev-ledger-entry",
    "id: SREV-235",
    "owner: Sandboxie/core/dll/gdi.h",
    "patched-source-level-after-official-gdi-signature-review",
    "srev-235-gdi-header-bitmapbits-signature.schema.json",
    "check-srev-235.py",
]:
    require(fragment, term, "ledger fragment")
    require(ledger, term, "combined ledger")

print("SREV-235 source gate passed")
