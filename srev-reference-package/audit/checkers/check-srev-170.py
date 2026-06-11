#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-170 failed: {label} missing {needle!r}")


def section(text: str, start: str, end: str) -> str:
    start_index = text.index(start)
    end_index = text.index(end, start_index)
    return text[start_index:end_index]


schema = json.loads((ROOT / "docs/plan/srev-170-arm64-driver-asm-abi-review.schema.json").read_text())
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-170 failed: schema is not draft-07")
if schema.get("id") != "ARM64_DRIVER_ASM_ABI_REVIEW":
    raise SystemExit("SREV-170 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "util_arm.asm owns ARM64 driver assembly wrappers for syscall invocation SepFilterToken invocation and the KiServiceInternal service bridge",
    "SboxDrv.vcxproj builds util_arm.asm for SbieDebug ARM64 and SbieRelease ARM64 with armasm64",
    "Sbie_InvokeSyscall_asm accepts at most 19 arguments and maps first eight integer pointer arguments to x0 through x7",
    "Sbie_InvokeSyscall_asm copies ninth and higher arguments to stack while preserving 16 byte stack alignment",
    "Sbie_SepFilterTokenHandler_asm maps five wrapper inputs into TokenObject six zero arguments SidCount SidPtr LengthIncrease and NewToken",
    "Sbie_CallZwServiceFunction_asm loads the twentieth wrapper argument from stack offset 0x58 into x16 before tail jumping to Driver_KiServiceInternal",
    "Linux source gate is not ARM64 WDK build unwind or runtime proof",
]:
    require(contracts, term, "schema")

asm = (ROOT / "Sandboxie/core/drv/util_arm.asm").read_text()
vcxproj = (ROOT / "Sandboxie/core/drv/SboxDrv.vcxproj").read_text()
syscall_c = (ROOT / "Sandboxie/core/drv/syscall.c").read_text()
token_c = (ROOT / "Sandboxie/core/drv/token.c").read_text()
driver_c = (ROOT / "Sandboxie/core/drv/driver.c").read_text()
spec = (ROOT / "docs/plan/srev-170-arm64-driver-asm-abi-review.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-170.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    '<CustomBuild Include="util_arm.asm">',
    "'$(Configuration)|$(Platform)'=='SbieRelease|ARM64'",
    "'$(Configuration)|$(Platform)'=='SbieDebug|ARM64'",
    "armasm64  -nologo",
    "'$(Configuration)|$(Platform)'=='SbieRelease|x64'\">true</ExcludedFromBuild>",
    "'$(Configuration)|$(Platform)'=='SbieDebug|x64'\">true</ExcludedFromBuild>",
]:
    require(vcxproj, term, "SboxDrv util_arm build target")

invoke = section(
    asm,
    "Sbie_InvokeSyscall_asm PROC",
    "Sbie_SepFilterTokenHandler_asm PROC",
)
for term in [
    "stp         fp,lr,[sp,#-0x10]!",
    "sub         sp,sp,#0x60",
    "cmp         w9,#0x13",
    "mov         x0, 0x001C",
    "movk        x0, 0xC000, lsl 16",
    "add         x12,x12,#0x40",
    "str         x13,[x14]",
    "ldr         x7,[x8,#0x38]",
    "ldr         x0,[x8]",
    "blr         x10",
    "ldp         fp,lr,[sp],#0x10",
]:
    require(invoke, term, "Sbie_InvokeSyscall_asm")

sep = section(
    asm,
    "Sbie_SepFilterTokenHandler_asm PROC",
    "Sbie_CallZwServiceFunction_asm PROC",
)
for term in [
    "ldr  x9, =Token_SepFilterToken",
    "ldr  x8, [x9]",
    "mov  x0, x0",
    "stp  x3, x4, [sp, #8]",
    "str  x2, [sp]",
    "mov  x7, x1",
    "movz x6, #0",
    "movz x1, #0",
    "blr  x8",
]:
    require(sep, term, "Sbie_SepFilterTokenHandler_asm")

zw = section(
    asm,
    "Sbie_CallZwServiceFunction_asm PROC",
    "    END",
)
for term in [
    "ldr  x16,[sp,#0x58]",
    "ldr  x9, =Driver_KiServiceInternal",
    "ldr  x8, [x9]",
    "br   x8",
]:
    require(zw, term, "Sbie_CallZwServiceFunction_asm")

for term in [
    "status = Sbie_InvokeSyscall_asm(entry->ntos_func, entry->param_count, stack);",
    "_FX NTSTATUS Sbie_SepFilterTokenHandler_asm(void* TokenObject, ULONG_PTR SidCount, ULONG_PTR SidPtr, ULONG_PTR LengthIncrease, void** NewToken);",
    "status = Sbie_SepFilterTokenHandler_asm(TokenObject, SidCount, SidPtr, LengthIncrease, NewToken);",
    "Sbie_CallZwServiceFunction_asm((ULONG_PTR)TokenHandle",
    "Driver_FindKiServiceInternal();",
]:
    source = "\n".join([syscall_c, token_c, driver_c])
    require(source, term, "call site topology")

for term in [
    "### SREV-170: ARM64 Driver Assembly ABI Review",
    "ARM64_DRIVER_ASM_ABI_REVIEW",
    "srev-170-arm64-driver-asm-abi-review.schema.json",
    "Sandboxie/core/drv/util_arm.asm",
    "Sbie_InvokeSyscall_asm",
    "Sbie_SepFilterTokenHandler_asm",
    "Sbie_CallZwServiceFunction_asm",
    "armasm64",
    "ARM64 WDK driver build",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-170 schema/source gate passed")
