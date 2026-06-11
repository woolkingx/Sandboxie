#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-282 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-282 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-282-chrome-flash-volume-info-dormant-hook.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-282 failed: schema is not draft-07")
if schema.get("id") != "CHROME_FLASH_VOLUME_INFO_DORMANT_HOOK":
    raise SystemExit("SREV-282 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/dll/file_init.c":
    raise SystemExit("SREV-282 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "GetVolumeInformationW retrieves file-system and volume information",
    "lpRootPathName may be NULL",
    "output pointers are optional",
    "buffer sizes are ignored when the corresponding output buffer is absent",
    "hook registration remains inactive",
    "all-null predicate body remains inactive",
    "future revival requires Windows proof",
    "SREV-273 and SREV-279 own active adjacent volume-info behavior",
    "this SREV changes comments and proof only",
]:
    require(contracts, term, "schema")

file_init = (ROOT / "Sandboxie/core/dll/file_init.c").read_text()
file_misc = (ROOT / "Sandboxie/core/dll/file_misc.c").read_text()
spec = (ROOT / "docs/plan/srev-282-chrome-flash-volume-info-dormant-hook.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-282.md").read_text()
srev_273 = (ROOT / "docs/plan/ledger/srev-273.md").read_text()
srev_279 = (ROOT / "docs/plan/ledger/srev-279.md").read_text()

init_start = file_init.index("SREV-282: dormant GetVolumeInformationW registration")
init_end = file_init.index("void* WriteProcessMemory", init_start)
init_block = file_init[init_start:init_end]

for term in [
    "SREV-282: dormant GetVolumeInformationW registration is kept inactive.",
    "Active volume-info ownership stays with NtQueryVolumeInformationFile",
    "and GetVolumeInformationByHandleW paths until Windows proof revives it.",
    "//void *GetVolumeInformationW =",
    "\"GetVolumeInformationW\"",
    "//SBIEDLL_HOOK(File_,GetVolumeInformationW);",
]:
    require(init_block, term, "file_init dormant registration")

for stale in [
    "$Workaround$ - 3rd party fix",
    "support for Google Chrome flash plugin process",
]:
    reject(init_block, stale, "file_init stale comment")

misc_start = file_misc.index("//_FX BOOL File_GetVolumeInformationW(")
misc_end = file_misc.index("// File_GetTempPathW", misc_start)
misc_block = file_misc[misc_start:misc_end]

for term in [
    "SREV-282: dormant Chrome Flash all-null probe path. Keep this body",
    "inactive unless Windows proof revives the matching registration in",
    "file_init.c and defines a current caller contract.",
    "//    if (Dll_ChromeSandbox &&",
    "//        lpVolumeNameBuffer == NULL && nVolumeNameSize == 0 &&",
    "//        lpVolumeSerialNumber == NULL && lpMaximumComponentLength == NULL &&",
    "//        lpFileSystemFlags == NULL &&",
    "//        lpFileSystemNameBuffer == NULL && nFileSystemNameSize == 0) {",
    "//        return TRUE;",
    "//    return __sys_GetVolumeInformationW(",
]:
    require(misc_block, term, "file_misc dormant body")

for stale in [
    "the flash plugin process of Google Chrome issues a special form",
    "this fails",
    "to work around this",
    "$Workaround$ - 3rd party fix",
]:
    reject(misc_block, stale, "file_misc stale comment")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "CHROME_FLASH_VOLUME_INFO_DORMANT_HOOK",
    "srev-282-chrome-flash-volume-info-dormant-hook.schema.json",
    "GetVolumeInformationW",
    "lpRootPathName",
    "SREV-273",
    "SREV-279",
]:
    require(spec, term, "spec")

for term in [
    "GetFinalPathNameByHandleW",
    "volume-name flags",
    "caller-visible final-path presentation",
]:
    require(srev_273, term, "SREV-273 adjacency")

for term in [
    "File_NtQueryVolumeInformationFile",
    "FileFsDeviceInformation",
    "VOLUME_DEVICE_INFO_NAMED_PIPE_FAST_PATH",
]:
    require(srev_279, term, "SREV-279 adjacency")

for term in [
    "### SREV-282: Chrome Flash Volume-Info Dormant Hook",
    "CHROME_FLASH_VOLUME_INFO_DORMANT_HOOK",
    "srev-282-chrome-flash-volume-info-dormant-hook.schema.json",
    "Sandboxie/core/dll/file_init.c",
    "Sandboxie/core/dll/file_misc.c",
    "GetVolumeInformationW",
    "SREV-273",
    "SREV-279",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-282 source gate passed")
