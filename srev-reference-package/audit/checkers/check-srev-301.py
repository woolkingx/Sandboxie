#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-301 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-301 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-301-ipc-firefox-section-view-protection-boundary.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-301 failed: schema is not draft-07")
if schema.get("id") != "IPC_FIREFOX_SECTION_VIEW_PROTECTION_BOUNDARY":
    raise SystemExit("SREV-301 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/dll/ipc.c":
    raise SystemExit("SREV-301 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "Ipc_NtMapViewOfSection owns only the Firefox remote non-image section view protection policy",
    "ZwMapViewOfSection owns the requested view protection compatibility with the section page protection",
    "NtQuerySection(SectionBasicInformation) owns the local SEC_IMAGE exclusion evidence",
    "SREV-283 owns the adjacent WriteProcessMemory suppression for NtMapViewOfSection export-address targets",
    "SREV-301 changes comments and proof only; no NtMapViewOfSection behavior changes",
]:
    require(contracts, term, "schema")

ipc = (ROOT / "Sandboxie/core/dll/ipc.c").read_text()
spec = (ROOT / "docs/plan/srev-301-ipc-firefox-section-view-protection-boundary.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-301.md").read_text()
srev_283 = "\n".join([
    (ROOT / "docs/plan/ledger/srev-283.md").read_text(),
    (ROOT / "docs/plan/srev-283-wpm-ntdll-patch-suppression-owner.md").read_text(),
    (ROOT / "docs/plan/srev-283-wpm-ntdll-patch-suppression-owner.schema.json").read_text(),
])

start = ipc.index("_FX NTSTATUS Ipc_NtMapViewOfSection(")
end = ipc.index("// Ipc_NtCreateSymbolicLinkObject", start)
func = ipc[start:end]

for term in [
    "if (Dll_ImageType == DLL_IMAGE_MOZILLA_FIREFOX) { // Firefox 146+",
    "if (ProcessHandle != currentProcess && ProcessHandle != INVALID_HANDLE_VALUE) {",
    "if (Protect == PAGE_EXECUTE_READ) {",
    "NTSTATUS status = NtQuerySection(SectionHandle, SectionBasicInformation, &sbi, sizeof(sbi), NULL);",
    "if (NT_SUCCESS(status) &&  (sbi.AllocationAttributes & SEC_IMAGE) == 0) {",
    "SREV-301: Firefox 146+ maps this non-image execute",
    "section into a child process so the child-side SbieDll",
    "startup can write its local patch bytes. ZwMapViewOfSection",
    "requires non-image view protection to stay compatible with",
    "the section's creation protection; Windows runtime proof",
    "owns the Firefox version and section-protection matrix.",
    "Protect = PAGE_EXECUTE_READWRITE;",
    "status = __sys_NtMapViewOfSection(",
]:
    require(func, term, "Ipc_NtMapViewOfSection")

for stale in [
    "NtProtectVirtualMemory will bug out",
    "BAM: Firefox NtMapViewOfSection hack",
    "Not an image section, likely the thunk allocation",
]:
    reject(func, stale, "source wording")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "IPC_FIREFOX_SECTION_VIEW_PROTECTION_BOUNDARY",
    "STATUS_SECTION_PROTECTION",
    "SREV-283 owns the adjacent Firefox/Thunderbird",
    "comment-only source clarification, no behavior change",
    "No behavior changed: the Firefox image-type check",
]:
    require(spec, term, "spec")

for term in [
    "WPM_NTDLL_PATCH_SUPPRESSION_OWNER",
    "the suppression branch is legal only for NtSetInformationThread and NtMapViewOfSection export-address targets",
    "SREV-075 output gate adjacency",
]:
    require(srev_283, term, "SREV-283 adjacency")

for term in [
    "### SREV-301: IPC Firefox Section View Protection Boundary",
    "IPC_FIREFOX_SECTION_VIEW_PROTECTION_BOUNDARY",
    "srev-301-ipc-firefox-section-view-protection-boundary.schema.json",
    "Sandboxie/core/dll/ipc.c",
    "Ipc_NtMapViewOfSection",
    "SREV-283",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-301 source gate passed")
