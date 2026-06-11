#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-075 failed: {label} missing {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-075-file-wpm-output-gate.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-075 failed: schema is not draft-07")
if schema.get("id") != "FILE_WPM_WORKAROUND_OUTPUT_GATE":
    raise SystemExit("SREV-075 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "lpNumberOfBytesWritten is optional and NULL must be ignored",
    "caller-owned output slot",
    "output slot write is protected",
    "ERROR_NOACCESS rather than crashing",
    "real __sys_WriteProcessMemory owner",
]:
    require(contracts, term, "schema")

src = (ROOT / "Sandboxie/core/dll/file_misc.c").read_text()
spec = (ROOT / "docs/plan/srev-075-file-wpm-output-gate.md").read_text()
ledger = read_combined_ledger(ROOT)

start = src.index("BOOL File_WriteProcessMemory(")
fallback = "return __sys_WriteProcessMemory(hProcess, lpBaseAddress, lpBuffer, nSize, lpNumberOfBytesWritten);"
end = src.index(fallback, start) + len(fallback)
func = src[start:end]

for term in [
    "Dll_ImageType == DLL_IMAGE_MOZILLA_FIREFOX || Dll_ImageType == DLL_IMAGE_MOZILLA_THUNDERBIRD",
    "lpBaseAddress == GetProcAddress(Dll_Ntdll, \"NtSetInformationThread\")",
    "lpBaseAddress == GetProcAddress(Dll_Ntdll, \"NtMapViewOfSection\")",
    "if (lpNumberOfBytesWritten) {\n                __try {\n                    *lpNumberOfBytesWritten = nSize;",
    "} __except (EXCEPTION_EXECUTE_HANDLER) {\n                    SetLastError(ERROR_NOACCESS);\n                    return FALSE;\n                }",
    "return TRUE; // ignore",
    "return __sys_WriteProcessMemory(hProcess, lpBaseAddress, lpBuffer, nSize, lpNumberOfBytesWritten);",
]:
    require(func, term, "File_WriteProcessMemory source")

if func.index("__try") > func.index("*lpNumberOfBytesWritten = nSize;"):
    raise SystemExit("SREV-075 failed: output write appears before SEH gate")
if "*lpNumberOfBytesWritten = nSize;\n            }\n            return TRUE; // ignore" in func:
    raise SystemExit("SREV-075 failed: stale ungated output write remains")
if func.index("return TRUE; // ignore") > func.index("return __sys_WriteProcessMemory"):
    raise SystemExit("SREV-075 failed: fake-success return appears after real fallback")

for term in [
    "https://learn.microsoft.com/en-us/windows/win32/api/memoryapi/nf-memoryapi-writeprocessmemory",
    "srev-075-file-wpm-output-gate.schema.json",
    "ERROR_NOACCESS",
]:
    require(spec, term, "spec")

for term in [
    "### SREV-075: WriteProcessMemory Workaround Output Gate",
    "FILE_WPM_WORKAROUND_OUTPUT_GATE",
    "srev-075-file-wpm-output-gate.schema.json",
]:
    require(ledger, term, "ledger")

print("SREV-075 schema/source gate passed")
