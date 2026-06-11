#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-158 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-158 failed: {label} still contains {needle!r}")


def section(text: str, start: str, end: str) -> str:
    start_index = text.index(start)
    end_index = text.index(end, start_index)
    return text[start_index:end_index]


schema = json.loads(
    (ROOT / "docs/plan/srev-158-ole-hglobal-lock-and-cida-copy-gates.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-158 failed: schema is not draft-07")
if schema.get("id") != "OLE_HGLOBAL_LOCK_AND_CIDA_COPY_GATES":
    raise SystemExit("SREV-158 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "Every active GlobalLock result dereferenced by ole.cpp must be non-null",
    "Every successful active GlobalLock in these copy paths must be followed by GlobalUnlock",
    "Failed output HGLOBAL locks free the newly allocated handle",
    "XDataObject::GetData does not publish a caller-visible STGMEDIUM unless both source and destination HGLOBAL locks succeed",
    "CFSTR_SHELLIDLIST CIDA offset zero copies the rewritten parent PIDL and child offsets copy GetPidl(count)",
    "does not change supported clipboard formats sandbox path translation policy drag/drop scheduling or inactive virtual-file extraction",
    "Linux source gate is not Windows runtime proof",
]:
    require(contracts, term, "schema")

source = (ROOT / "Sandboxie/core/dll/ole.cpp").read_text()
spec = (ROOT / "docs/plan/srev-158-ole-hglobal-lock-and-cida-copy-gates.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-158.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

get_data = section(source, "_FX HRESULT XDataObject::GetData(", "//---------------------------------------------------------------------------\n// IDataObject::GetDataHere")
for term in [
    "void *ptrSrc = GlobalLock(m_hDrop);",
    "void *ptrDst = GlobalLock(hGlobal);",
    "if (! ptrSrc || ! ptrDst) {",
    "if (ptrSrc)\n                    GlobalUnlock(m_hDrop);",
    "if (ptrDst)\n                    GlobalUnlock(hGlobal);",
    "GlobalFree(hGlobal);",
    "hr = STG_E_MEDIUMFULL;",
    "pmedium->tymed = TYMED_HGLOBAL;",
    "pmedium->hGlobal = hGlobal;",
    "pmedium->pUnkForRelease = NULL;",
]:
    require(get_data, term, "XDataObject::GetData")
if not (
    get_data.index("if (! ptrSrc || ! ptrDst) {")
    < get_data.index("pmedium->tymed = TYMED_HGLOBAL;")
):
    raise SystemExit("SREV-158 failed: GetData publishes STGMEDIUM before lock failure gate")

hdrop = section(source, "_FX HGLOBAL XDataObject::InitFormatHDrop(", "//---------------------------------------------------------------------------\n// OpenFileFromHDrop")
for term in [
    "void *ptr = GlobalLock(hData);",
    "if (ptr) {",
    "memcpy(ptr, DropFiles, len);",
    "GlobalUnlock(hData);",
    "} else {\n                GlobalFree(hData);\n                hData = NULL;",
]:
    require(hdrop, term, "InitFormatHDrop")

file_a = section(source, "_FX HGLOBAL XDataObject::InitFormatFileNameA(", "//---------------------------------------------------------------------------\n// InitFormatFileNameW")
for term in [
    "char *FileNameA = (char *)GlobalLock(hData);",
    "if (! FileNameA)\n            return NULL;",
    "hFile = CreateFileA(FileNameA,",
    "ansi.Buffer = (UCHAR *)GlobalLock(hDataRet);",
    "if (ansi.Buffer) {",
    "RtlUnicodeStringToAnsiString(&ansi, &uni, FALSE);",
    "GlobalUnlock(hDataRet);",
    "} else {\n                    GlobalFree(hDataRet);\n                    hDataRet = NULL;",
]:
    require(file_a, term, "InitFormatFileNameA")
if not (file_a.index("if (! FileNameA)") < file_a.index("hFile = CreateFileA(FileNameA,")):
    raise SystemExit("SREV-158 failed: FileNameA lock gate is after CreateFileA")

file_w = section(source, "_FX HGLOBAL XDataObject::InitFormatFileNameW(", "//---------------------------------------------------------------------------\n// InitFormatIdList")
for term in [
    "WCHAR *FileNameW = (WCHAR *)GlobalLock(hData);",
    "if (! FileNameW)\n            return NULL;",
    "hFile = CreateFileW(FileNameW,",
    "WCHAR *ptr = (WCHAR *)GlobalLock(hDataRet);",
    "if (ptr) {",
    "memcpy(ptr, name, len);",
    "GlobalUnlock(hDataRet);",
    "} else {\n                    GlobalFree(hDataRet);\n                    hDataRet = NULL;",
]:
    require(file_w, term, "InitFormatFileNameW")
if not (file_w.index("if (! FileNameW)") < file_w.index("hFile = CreateFileW(FileNameW,")):
    raise SystemExit("SREV-158 failed: FileNameW lock gate is after CreateFileW")

idlist = section(source, "_FX HGLOBAL XDataObject::InitFormatIdList(", "//---------------------------------------------------------------------------\n// Ole_ReleaseStgMedium")
for term in [
    "CIDA *pIdList = (CIDA *)GlobalLock(hData);",
    "if (! pIdList)\n        return NULL;",
    "HGLOBAL hDataRet = NULL;",
    "UCHAR *ptr0 = (UCHAR *)GlobalLock(hDataRet);",
    "if (ptr0) {",
    "memcpy(ptr, pidl, pidl_len);",
    "offsets[0] = (USHORT)(ULONG_PTR)(ptr - ptr0);",
    "memcpy(ptr, GetPidl(count), pidl_len);",
    "offsets[count] = (USHORT)(ULONG_PTR)(ptr - ptr0);",
    "} else {\n            GlobalFree(hDataRet);\n            hDataRet = NULL;",
]:
    require(idlist, term, "InitFormatIdList")

child_loop = idlist[
    idlist.index("for (count = 1; count <= pIdList->cidl; ++count)", idlist.index("if (ptr0) {")):
    idlist.index("GlobalUnlock(hDataRet);", idlist.index("if (ptr0) {"))
]
require(child_loop, "pidl_len = pILGetSize(GetPidl(count));", "CIDA child loop")
require(child_loop, "memcpy(ptr, GetPidl(count), pidl_len);", "CIDA child loop")
reject(child_loop, "memcpy(ptr, pidl, pidl_len);", "stale parent PIDL child copy")

for term in [
    "### SREV-158: Ole HGLOBAL Lock And CIDA Copy Gates",
    "OLE_HGLOBAL_LOCK_AND_CIDA_COPY_GATES",
    "srev-158-ole-hglobal-lock-and-cida-copy-gates.schema.json",
    "Sandboxie/core/dll/ole.cpp",
    "GlobalLock",
    "STGMEDIUM",
    "TYMED_HGLOBAL",
    "CFSTR_SHELLIDLIST",
    "CIDA",
    "GetPidl(count)",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-158 schema/source gate passed")
