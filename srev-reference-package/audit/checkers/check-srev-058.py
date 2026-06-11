#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-058 failed: {label} missing {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-058-dllhook-instruction-cache.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-058 failed: schema is not draft-07")
if schema.get("id") != "DLLHOOK_INSTRUCTION_CACHE_COHERENCY":
    raise SystemExit("SREV-058 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "VirtualProtect changes committed page protection",
    "Generated or modified executable code must be followed by FlushInstructionCache",
    "E9 operand rewrite must flush the 4-byte operand span",
    "trampoline writer must flush the generated trampoline buffer",
    "source function detour writer must flush the RegionBase and RegionSize span",
]:
    require(contracts, term, "schema")

src = (ROOT / "Sandboxie/core/dll/dllhook.c").read_text()
spec = (ROOT / "docs/plan/srev-058-dllhook-instruction-cache.md").read_text()
ledger = read_combined_ledger(ROOT)

start = src.index("_FX void *SbieDll_Hook_x86(")
end = src.index("#if defined(_M_ARM64) || defined(_M_ARM64EC)", start)
hook_x86 = src[start:end]

for term in [
    "*(ULONG *)func = (ULONG)diff;\n        VirtualProtect(func, 4, prot, &dummy_prot);\n        FlushInstructionCache(GetCurrentProcess(), func, 4);",
    "if (SbieApi_HookTramp(SourceFunc, tramp) != 0)",
    "FlushInstructionCache(GetCurrentProcess(), tramp, 128);",
    "VirtualProtect(RegionBase, RegionSize, prot, &dummy_prot);\n    FlushInstructionCache(GetCurrentProcess(), RegionBase, RegionSize);",
]:
    require(hook_x86, term, "SbieDll_Hook_x86 source")

arm_start = src.index("void* SbieDll_Hook_arm(")
arm_end = src.index("// SbieDll_HookFunc", arm_start)
hook_arm64 = src[arm_start:arm_end]
for term in [
    "FlushInstructionCache(GetCurrentProcess(), pbJump, SIZE_OF_JMP);",
    "FlushInstructionCache(GetCurrentProcess(), RegionBase, RegionSize);",
    "FlushInstructionCache(GetCurrentProcess(), pTrampoline->rbCode, pTrampoline->cbCode + SIZE_OF_JMP);",
]:
    require(hook_arm64, term, "ARM64 precedent")

for term in [
    "https://learn.microsoft.com/en-us/windows/win32/api/memoryapi/nf-memoryapi-virtualprotect",
    "https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-flushinstructioncache",
    "srev-058-dllhook-instruction-cache.schema.json",
]:
    require(spec, term, "spec")

for term in [
    "### SREV-058: DLL Hook Instruction Cache Coherency",
    "DLLHOOK_INSTRUCTION_CACHE_COHERENCY",
    "srev-058-dllhook-instruction-cache.schema.json",
]:
    require(ledger, term, "ledger")

print("SREV-058 schema/source gate passed")
