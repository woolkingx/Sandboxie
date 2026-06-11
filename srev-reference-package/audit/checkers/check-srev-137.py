#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-137 failed: {label} missing {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-137-ldr-init-entrypoint-instruction-cache.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-137 failed: schema is not draft-07")
if schema.get("id") != "LDR_INIT_ENTRYPOINT_INSTRUCTION_CACHE_COHERENCY":
    raise SystemExit("SREV-137 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "VirtualProtect changes committed page protection but does not by itself prove instruction-cache coherency",
    "Generated or modified executable code must be followed by FlushInstructionCache",
    "Ldr_Inject_Init must flush entrypoint, LDR_INJECT_NUM_SAVE_BYTES after writing the architecture-specific entrypoint stub",
    "Ldr_Inject_Entry must flush entrypoint, LDR_INJECT_NUM_SAVE_BYTES after restoring saved original bytes and restoring page protection",
    "The entrypoint mutation range remains LDR_INJECT_NUM_SAVE_BYTES on ARM64, x64, and x86",
]:
    require(contracts, term, "schema")

source = (ROOT / "Sandboxie/core/dll/ldr_init.c").read_text()
spec = (ROOT / "docs/plan/srev-137-ldr-init-entrypoint-instruction-cache.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-137.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

init = source[
    source.index("_FX void Ldr_Inject_Init"):
    source.index("//---------------------------------------------------------------------------\n// Ldr_Inject_Entry")
]
for term in [
    "memcpy(Ldr_Inject_SaveBytes, entrypoint, LDR_INJECT_NUM_SAVE_BYTES);",
    "VirtualProtect(entrypoint, LDR_INJECT_NUM_SAVE_BYTES,",
    "PAGE_EXECUTE_READWRITE, &Ldr_Inject_OldProtect)",
    "*aCode++ = 0x10000000;",
    "*(ULONG_PTR*)aCode = (ULONG_PTR)Ldr_Inject_Entry64;",
    "entrypoint[0] = 0x48;",
    "*(ULONG_PTR *)(entrypoint + 2) = (ULONG_PTR)Ldr_Inject_Entry64;",
    "entrypoint[10] = 0xFF;",
    "*entrypoint = 0xE8;",
    "(UCHAR *)Ldr_Inject_Entry32 - (entrypoint + 5);",
    "NtFlushInstructionCache(GetCurrentProcess(), entrypoint, LDR_INJECT_NUM_SAVE_BYTES);",
]:
    require(init, term, "Ldr_Inject_Init source")

if init.index("NtFlushInstructionCache(GetCurrentProcess(), entrypoint, LDR_INJECT_NUM_SAVE_BYTES);") < init.index("#endif _WIN64"):
    raise SystemExit("SREV-137 failed: initial patch flush is still inside one architecture branch")
if init.index("NtFlushInstructionCache(GetCurrentProcess(), entrypoint, LDR_INJECT_NUM_SAVE_BYTES);") < init.index("(UCHAR *)Ldr_Inject_Entry32 - (entrypoint + 5);"):
    raise SystemExit("SREV-137 failed: initial patch flush occurs before x86 patch write")

entry = source[
    source.index("_FX void* Ldr_Inject_Entry"):
    source.index("if (!g_bHostInject)", source.index("_FX void* Ldr_Inject_Entry"))
]
for term in [
    "entrypoint = (UCHAR*)pPtr;",
    "entrypoint = (UCHAR*)g_entrypoint;",
    "entrypoint = ((UCHAR *)*pPtr) - LDR_INJECT_NUM_SAVE_BYTES;",
    "VirtualProtect(entrypoint, LDR_INJECT_NUM_SAVE_BYTES,",
    "PAGE_EXECUTE_READWRITE, &dummy_prot);",
    "memcpy(entrypoint, Ldr_Inject_SaveBytes, LDR_INJECT_NUM_SAVE_BYTES);",
    "Ldr_Inject_OldProtect, &dummy_prot);",
    "NtFlushInstructionCache(GetCurrentProcess(), entrypoint, LDR_INJECT_NUM_SAVE_BYTES);",
]:
    require(entry, term, "Ldr_Inject_Entry source")

if "#ifdef _M_ARM64\n    NtFlushInstructionCache" in entry:
    raise SystemExit("SREV-137 failed: restore flush is still ARM64-only")
if entry.index("NtFlushInstructionCache(GetCurrentProcess(), entrypoint, LDR_INJECT_NUM_SAVE_BYTES);") < entry.index("memcpy(entrypoint, Ldr_Inject_SaveBytes, LDR_INJECT_NUM_SAVE_BYTES);"):
    raise SystemExit("SREV-137 failed: restore flush occurs before byte restore")
if entry.index("NtFlushInstructionCache(GetCurrentProcess(), entrypoint, LDR_INJECT_NUM_SAVE_BYTES);") < entry.index("Ldr_Inject_OldProtect, &dummy_prot);"):
    raise SystemExit("SREV-137 failed: restore flush occurs before protection restore")

for term in [
    "### SREV-137: Ldr Init Entrypoint Instruction Cache Coherency",
    "LDR_INIT_ENTRYPOINT_INSTRUCTION_CACHE_COHERENCY",
    "srev-137-ldr-init-entrypoint-instruction-cache.schema.json",
    "NtFlushInstructionCache",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-137 schema/source gate passed")
