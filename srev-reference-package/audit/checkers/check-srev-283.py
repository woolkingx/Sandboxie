#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-283 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-283 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-283-wpm-ntdll-patch-suppression-owner.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-283 failed: schema is not draft-07")
if schema.get("id") != "WPM_NTDLL_PATCH_SUPPRESSION_OWNER":
    raise SystemExit("SREV-283 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/dll/file_misc.c":
    raise SystemExit("SREV-283 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "WriteProcessMemory writes data to memory in a specified process",
    "target range must be accessible",
    "lpNumberOfBytesWritten is optional",
    "Firefox/Thunderbird ntdll patch suppression branch",
    "NtSetInformationThread and NtMapViewOfSection export-address targets",
    "SREV-075 owns the fake-success output-parameter gate",
    "non-matching writes must flow to the real __sys_WriteProcessMemory owner",
    "this SREV changes comments and proof only",
]:
    require(contracts, term, "schema")

src = (ROOT / "Sandboxie/core/dll/file_misc.c").read_text()
spec = (ROOT / "docs/plan/srev-283-wpm-ntdll-patch-suppression-owner.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-283.md").read_text()
srev_075 = (ROOT / "docs/plan/ledger/srev-075.md").read_text()

start = src.index("BOOL File_WriteProcessMemory(")
fallback = "return __sys_WriteProcessMemory(hProcess, lpBaseAddress, lpBuffer, nSize, lpNumberOfBytesWritten);"
end = src.index(fallback, start) + len(fallback)
func = src[start:end]

for term in [
    "SREV-283: suppress only Firefox/Thunderbird writes to selected",
    "ntdll export addresses.  SREV-075 owns the fake-success output",
    "contract when this branch bypasses the real WriteProcessMemory owner.",
    "if (!Dll_CompartmentMode)",
    "Dll_ImageType == DLL_IMAGE_MOZILLA_FIREFOX || Dll_ImageType == DLL_IMAGE_MOZILLA_THUNDERBIRD",
    "lpBaseAddress == GetProcAddress(Dll_Ntdll, \"NtSetInformationThread\")",
    "lpBaseAddress == GetProcAddress(Dll_Ntdll, \"NtMapViewOfSection\")",
    "if (lpNumberOfBytesWritten) {\n                __try {\n                    *lpNumberOfBytesWritten = nSize;",
    "SetLastError(ERROR_NOACCESS);",
    "return TRUE; // ignore",
    fallback,
]:
    require(func, term, "File_WriteProcessMemory source")

reject(func, "$Workaround$ - 3rd party fix", "File_WriteProcessMemory stale comment")

if func.index("return TRUE; // ignore") > func.index(fallback):
    raise SystemExit("SREV-283 failed: fake-success return appears after real fallback")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "WPM_NTDLL_PATCH_SUPPRESSION_OWNER",
    "srev-283-wpm-ntdll-patch-suppression-owner.schema.json",
    "SREV-075",
    "NtSetInformationThread",
    "NtMapViewOfSection",
    "__sys_WriteProcessMemory",
]:
    require(spec, term, "spec")

for term in [
    "FILE_WPM_WORKAROUND_OUTPUT_GATE",
    "lpNumberOfBytesWritten",
    "ERROR_NOACCESS",
    "Firefox/Thunderbird suppressed `ntdll` patch write",
]:
    require(srev_075, term, "SREV-075 adjacency")

for term in [
    "### SREV-283: WriteProcessMemory NTDLL Patch Suppression Owner",
    "WPM_NTDLL_PATCH_SUPPRESSION_OWNER",
    "srev-283-wpm-ntdll-patch-suppression-owner.schema.json",
    "Sandboxie/core/dll/file_misc.c",
    "WriteProcessMemory",
    "SREV-075",
    "NtSetInformationThread",
    "NtMapViewOfSection",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-283 source gate passed")
