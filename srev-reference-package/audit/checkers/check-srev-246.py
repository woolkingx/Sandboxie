#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-246 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-246 failed: {label} still contains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-246-dllhook-unity-nop-padding-boundary.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-246 failed: schema is not draft-07")
if schema.get("id") != "DLLHOOK_UNITY_NOP_PADDING_BOUNDARY":
    raise SystemExit("SREV-246 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "hook_tramp.c owns copied-instruction byte counting",
    "dllhook.c owns only the active detour envelope",
    "entry detour transfers normal control flow",
    "NOP-padding from UsedCount to ByteCount changes the writable code span",
    "old Unity breakage is runtime compatibility evidence",
    "future NOP-padding patch must first publish a checked ByteCount and UsedCount contract",
    "does not change detour bytes trampoline generation page protection cache flushing or hook policy",
]:
    require(contracts, term, "schema")

dllhook = (ROOT / "Sandboxie/core/dll/dllhook.c").read_text()
hook_tramp = (ROOT / "Sandboxie/core/dll/hook_tramp.c").read_text()
spec = (ROOT / "docs/plan/srev-246-dllhook-unity-nop-padding-boundary.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-246.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "if (SbieApi_HookTramp(SourceFunc, tramp) != 0)",
    "FlushInstructionCache(GetCurrentProcess(), tramp, 128);",
    "//ULONG ByteCount = *(ULONG*)(tramp + 80);",
    "//ULONG UsedCount = 0;",
    "func[0] = 0xE9;",
    "*(USHORT *)&func[0] = 0x25ff;",
    "VirtualProtect(RegionBase, RegionSize, prot, &dummy_prot);",
    "FlushInstructionCache(GetCurrentProcess(), RegionBase, RegionSize);",
    "Do not pad the moved instruction tail with NOPs here.",
    "write span to HookTramp's ByteCount needs a Unity runtime gate.",
    "//for(; UsedCount < ByteCount; UsedCount++)",
    "//\tfunc[UsedCount] = 0x90; // nop",
]:
    require(dllhook, term, "dllhook source")

for stale in [
    "// just in case nop out the rest of the code we moved to the trampoline",
    "// ToDo: why does this break unity games",
    "because it has broken Unity games in the past.",
]:
    reject(dllhook, stale, "stale symptom-only comment")

for term in [
    "void *SysProc, ULONG *ByteCount, BOOLEAN is64, BOOLEAN probe)",
    "*ByteCount = copylen;",
    "tramp->target = src + ByteCount;",
    "tramp->count = ByteCount;",
    "while ((ULONG_PTR)(src - (UCHAR *)SourceFunc) < ByteCount)",
]:
    require(hook_tramp, term, "hook_tramp ByteCount owner")

for term in [
    "SREV-058 owns page-protection and instruction-cache coherency",
    "SREV-091 owns preserving third-party detour envelopes",
    "Comment-only source clarification",
    "Unity",
    "NOP padding",
]:
    require(spec, term, "spec local contract")

for term in [
    "### SREV-246: DLL Hook Unity NOP Padding Boundary",
    "DLLHOOK_UNITY_NOP_PADDING_BOUNDARY",
    "srev-246-dllhook-unity-nop-padding-boundary.schema.json",
    "Sandboxie/core/dll/dllhook.c",
    "hook_tramp.c",
    "Unity",
    "NOP padding",
    "Comment-only source clarification",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-246 source gate passed")
