#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-057 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-057 failed: {label} still contains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-057-file-init-box-root-path.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-057 failed: schema is not draft-07")
if schema.get("id") != "FILE_INIT_BOX_ROOT_PATH_PUBLICATION":
    raise SystemExit("SREV-057 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "UNICODE_STRING lengths are byte lengths",
    "wcscpy requires a valid destination buffer",
    "NTSTATUS results must be tested with NT_SUCCESS",
    "SbieApi_QueryProcessInfoStr passes inout_str_len as a UNICODE_STRING MaximumLength byte capacity",
    "raw-root fallback accepts only byte capacities that fit UNICODE_STRING.MaximumLength",
    "Dll_BoxFileDosPath is published only after allocation and translation succeed",
    "Dll_BoxFileRawPath is published only after allocation, query success, and non-empty string proof",
    "null global root path must have a zero length gate",
]:
    require(contracts, term, "schema")

src = (ROOT / "Sandboxie/core/dll/file_init.c").read_text()
file_src = (ROOT / "Sandboxie/core/dll/file.c").read_text()
sbieapi = (ROOT / "Sandboxie/core/dll/sbieapi.c").read_text()
spec = (ROOT / "docs/plan/srev-057-file-init-box-root-path.md").read_text()
ledger = read_combined_ledger(ROOT)

start = src.index("Dll_BoxFileDosPath = Dll_Alloc((Dll_BoxFilePathLen + 1) * sizeof(WCHAR));")
end = src.index("File_InitSnapshots();", start)
init = src[start:end]

sbie_start = sbieapi.index("_FX LONG SbieApi_QueryProcessInfoStr(")
sbie_end = sbieapi.index("// SbieApi_QueryBoxPath", sbie_start)
query_str = sbieapi[sbie_start:sbie_end]

for term in [
    "WCHAR *out_str,\n    ULONG *inout_str_len",
    "UniStr.Length = 0;",
    "UniStr.MaximumLength = (USHORT)*inout_str_len;",
    "UniStr.Buffer = (ULONG64)(ULONG_PTR)out_str;",
    "args->ext_data.val64 = (ULONG64)(ULONG_PTR)&UniStr;",
    "status = SbieApi_Ioctl(parms);",
    "if (!NT_SUCCESS(status))",
    "*out_str = L'\\0';",
]:
    require(query_str, term, "SbieApi_QueryProcessInfoStr shape")

for term in [
    "if (Dll_BoxFileDosPath) {\n        wcscpy((WCHAR *)Dll_BoxFileDosPath, Dll_BoxFilePath);",
    "if (!Dll_BoxFileDosPath)\n    {",
    "if (NT_SUCCESS(SbieApi_QueryProcessInfoStr(0, 'root', NULL, &BoxFileRawPathLen)) &&\n                BoxFileRawPathLen >= sizeof(WCHAR) && BoxFileRawPathLen <= 0xFFFF)",
    "WCHAR* BoxFileRawPath = Dll_AllocTemp(BoxFileRawPathLen);",
    "if (BoxFileRawPath && NT_SUCCESS(SbieApi_QueryProcessInfoStr(0, 'root', BoxFileRawPath, &BoxFileRawPathLen)) && *BoxFileRawPath)",
    "Dll_BoxFileRawPath = BoxFileRawPath;",
    "Dll_BoxFileRawPathLen = wcslen(Dll_BoxFileRawPath);",
    "Dll_BoxFileDosPath = Dll_Alloc(BoxFileRawPathLen);",
    "if (Dll_BoxFileDosPath) {\n                    wcscpy((WCHAR*)Dll_BoxFileDosPath, Dll_BoxFileRawPath);",
    "if(Dll_BoxFileDosPath)\n        Dll_BoxFileDosPathLen = wcslen(Dll_BoxFileDosPath);",
]:
    require(init, term, "file_init source")

for term in [
    "SREV-264: File_AltBoxPath is a legacy mount-point prefix fallback.",
    "Removal must first reprove the SREV-057 raw-root/mount-point matrix.",
    "Dll_BoxFilePath, Dll_BoxFilePathLen,",
    "Dll_BoxFileRawPath, Dll_BoxFileRawPathLen,",
    "File_AltBoxPath, File_AltBoxPathLen",
]:
    require(file_src, term, "file source")

reject(init, "Dll_BoxFileDosPath = Dll_Alloc((Dll_BoxFilePathLen + 1) * sizeof(WCHAR));\n    wcscpy", "file_init source")
reject(init, "Dll_BoxFileRawPath = Dll_AllocTemp(BoxFileRawPathLen);", "file_init source")
reject(init, "Dll_BoxFileDosPath = Dll_Alloc(BoxFileRawPathLen);\n                wcscpy", "file_init source")
reject(file_src, "ToDo: deprecated, remove - raw path is more reliable and covers all cases", "file source")

for term in [
    "https://learn.microsoft.com/en-us/windows/win32/api/ntdef/ns-ntdef-_unicode_string",
    "https://learn.microsoft.com/en-us/cpp/c-runtime-library/reference/strcpy-wcscpy-mbscpy",
    "https://learn.microsoft.com/en-us/windows-hardware/drivers/kernel/using-ntstatus-values",
    "SbieApi_QueryProcessInfoStr(ProcessId, info_type, out_str, inout_str_len)",
    "MaximumLength = (USHORT)*inout_str_len",
    "sizeof(WCHAR) <= BoxFileRawPathLen <=\n0xFFFF",
    "SREV-264",
    "File_AltBoxPath` as a legacy mount-point prefix",
    "srev-057-file-init-box-root-path.schema.json",
]:
    require(spec, term, "spec")

for term in [
    "### SREV-057: Box Root DOS Path Publication Boundary",
    "FILE_INIT_BOX_ROOT_PATH_PUBLICATION",
    "srev-057-file-init-box-root-path.schema.json",
    "SREV-264",
]:
    require(ledger, term, "ledger")

print("SREV-057 schema/source gate passed")
