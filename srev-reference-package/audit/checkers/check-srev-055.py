#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-055 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-055 failed: {label} still contains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-055-custom-sysfer-entrypoint-patch.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-055 failed: schema is not draft-07")
if schema.get("id") != "CUSTOM_SYSFER_ENTRYPOINT_PATCH":
    raise SystemExit("SREV-055 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "module base must be non-null",
    "DOS and NT signatures must be valid",
    "non-zero 4-byte span inside SizeOfImage",
    "only the patch span writable and executable",
    "FlushInstructionCache",
    "previous page protection must be restored",
]:
    require(contracts, term, "schema")

src = (ROOT / "Sandboxie/core/dll/custom.c").read_text()
spec = (ROOT / "docs/plan/srev-055-custom-sysfer-entrypoint-patch.md").read_text()
ledger = read_combined_ledger(ROOT)

start = src.index("_FX BOOLEAN Custom_SYSFER_DLL(")
end = src.index("// Handles ActivClient", start)
sysfer = src[start:end]

for term in [
    "SREV-055 owns this",
    "bounded entry-point patch for the SYSFER.DLL load path.",
    "ULONG_PTR base = (ULONG_PTR)hmodule;",
    "if (!base)\n        return TRUE;",
    "IMAGE_DOS_HEADER* dos_hdr = (IMAGE_DOS_HEADER*)base;",
    "dos_hdr->e_magic != IMAGE_DOS_SIGNATURE",
    "IMAGE_NT_HEADERS* nt_hdrs = (IMAGE_NT_HEADERS*)(base + dos_hdr->e_lfanew);",
    "nt_hdrs->Signature != IMAGE_NT_SIGNATURE",
    "IMAGE_OPTIONAL_HEADER* opt_hdr = &nt_hdrs->OptionalHeader;",
    "ULONG entry_rva = opt_hdr->AddressOfEntryPoint;",
    "ULONG image_size = opt_hdr->SizeOfImage;",
    "if (!entry_rva || entry_rva > image_size || image_size - entry_rva < sizeof(ULONG))",
    "UCHAR *entrypoint = (UCHAR *)(base + entry_rva);",
    "VirtualProtect(entrypoint, sizeof(ULONG), PAGE_EXECUTE_READWRITE, &old_prot)",
    "*(ULONG *)entrypoint = 0x00C301B0;",
    "FlushInstructionCache(GetCurrentProcess(), entrypoint, sizeof(ULONG));",
    "ULONG tmp_prot;",
    "VirtualProtect(entrypoint, sizeof(ULONG), old_prot, &tmp_prot);",
]:
    require(sysfer, term, "Custom_SYSFER_DLL")

reject(sysfer, "extern IMAGE_OPTIONAL_HEADER *Ldr_OptionalHeader", "Custom_SYSFER_DLL")
reject(sysfer, "base + opt_hdr->AddressOfEntryPoint", "Custom_SYSFER_DLL")
reject(sysfer, "VirtualProtect(entrypoint, 16", "Custom_SYSFER_DLL")
reject(sysfer, "workaround to nullify SYSFER.DLL", "Custom_SYSFER_DLL")

for term in [
    "https://learn.microsoft.com/en-us/windows/win32/debug/pe-format",
    "https://learn.microsoft.com/en-us/windows/win32/api/memoryapi/nf-memoryapi-virtualprotect",
    "https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-flushinstructioncache",
    "srev-055-custom-sysfer-entrypoint-patch.schema.json",
]:
    require(spec, term, "spec")

for term in [
    "### SREV-055: SYSFER Entry Point Patch Boundary",
    "CUSTOM_SYSFER_ENTRYPOINT_PATCH",
    "srev-055-custom-sysfer-entrypoint-patch.schema.json",
]:
    require(ledger, term, "ledger")

print("SREV-055 schema/source gate passed")
