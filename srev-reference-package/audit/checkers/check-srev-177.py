#!/usr/bin/env python3
import json
import re
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-177 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-177 failed: stale {label} still present")


def asm_proc(text: str, name: str) -> str:
    match = re.search(rf"^{re.escape(name)} PROC\b", text, re.M)
    if not match:
        raise SystemExit(f"SREV-177 failed: {name} PROC missing")
    end = re.search(r"^\s*ENDP\b", text[match.end():], re.M)
    if not end:
        raise SystemExit(f"SREV-177 failed: {name} ENDP missing")
    return text[match.start():match.end() + end.end()]


schema = json.loads((ROOT / "docs/plan/srev-177-arm64ec-api-instrumentation-argument-preservation.schema.json").read_text())
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-177 failed: schema is not draft-07")
if schema.get("id") != "ARM64EC_API_INSTRUMENTATION_ARGUMENT_PRESERVATION":
    raise SystemExit("SREV-177 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "util_EC.asm owns ARM64EC API instrumentation assembly state preservation",
    "dllhook.c emits ARM64EC API trace detours with x17 pointing at the trace entry header and x16 pointing at ApiInstrumentationAsm",
    "ApiInstrumentationAsm preserves x0-x7 before calling ApiInstrumentation",
    "ApiInstrumentationAsm passes pName in x0 and the saved argument frame in x1",
    "the saved argument frame begins at the saved x0 x1 pair and pArgs[-1] is the saved LR consumed as ReturnAddress",
    "ApiInstrumentationAsm preserves x16 x17 across the instrumentation call before loading the detour target from [x17]",
    "ApiInstrumentationAsm keeps SP 16-byte aligned across stack accesses and the C call",
    "RPC NDR ARM64EC wrappers keep their ARM64EC variadic stack pointer size contract and are not changed by this SREV",
    "SREV-177 does not change trace entry layout monitor logging RPC hook policy instrumentation callback policy or ARM64 native util_arm.asm",
    "Linux source gate is not Windows ARM64EC build runtime proof",
]:
    require(contracts, term, "schema")

util_ec = (ROOT / "Sandboxie/core/dll/util_EC.asm").read_text()
util_arm = (ROOT / "Sandboxie/core/dll/util_arm.asm").read_text()
dllhook = (ROOT / "Sandboxie/core/dll/dllhook.c").read_text()
trace = (ROOT / "Sandboxie/core/dll/trace.c").read_text()
vcxproj = (ROOT / "Sandboxie/core/dll/SboxDll.vcxproj").read_text()
rpcrt = (ROOT / "Sandboxie/core/dll/rpcrt.c").read_text()
spec = (ROOT / "docs/plan/srev-177-arm64ec-api-instrumentation-argument-preservation.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-177.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

api_ec = asm_proc(util_ec, "ApiInstrumentationAsm")
for term in [
    "stp     x6, x7, [sp, #-0x10]!",
    "stp     x4, x5, [sp, #-0x10]!",
    "stp     x2, x3, [sp, #-0x10]!",
    "stp     x0, x1, [sp, #-0x10]!",
    "stp     fp, lr, [sp, #-0x10]!",
    "x17 points at the trace",
    "saved x0-x7 frame begins at",
    "pArgs[-1] is the saved LR",
    "mov     x0, x17",
    "add     x0, x0, #8  ; pName",
    "mov     x1, sp",
    "add     x1, x1, #16 ; pArgs",
    "stp     x16, x17, [sp, #-0x10]!",
    "bl      ApiInstrumentation",
    "ldp     x16, x17, [sp], #0x10",
    "ldp     fp, lr, [sp], #0x10",
    "ldp     x0, x1, [sp], #0x10",
    "ldp     x2, x3, [sp], #0x10",
    "ldp     x4, x5, [sp], #0x10",
    "ldp     x6, x7, [sp], #0x10",
    "ldr     x16, [x17]",
    "br      x16",
]:
    require(api_ec, term, "util_EC ApiInstrumentationAsm")

reject(api_ec, "; invoke api entry instrumentation", "old incomplete ARM64EC API instrumentation comment")

api_arm = asm_proc(util_arm, "ApiInstrumentationAsm")
for term in [
    "stp     x6, x7, [sp, #-0x10]!",
    "stp     x4, x5, [sp, #-0x10]!",
    "ldp     x4, x5, [sp], #0x10",
    "ldp     x6, x7, [sp], #0x10",
]:
    require(api_arm, term, "native ARM64 comparison contract")

for proc in [
    "RpcRt_NdrClientCall2",
    "RpcRt_NdrClientCall3",
    "RpcRt_NdrAsyncClientCall",
    "RpcRt_Ndr64AsyncClientCall",
]:
    body = asm_proc(util_ec, proc)
    require(body, "x4 first argument on stack", f"{proc} ARM64EC variadic stack pointer comment")
    require(body, "x5 arguments size on stack", f"{proc} ARM64EC variadic stack size comment")

for term in [
    "<Command Condition=\"'$(Configuration)|$(Platform)'=='SbieDebug|ARM64EC'\">ml64",
    "<Command Condition=\"'$(Configuration)|$(Platform)'=='SbieRelease|ARM64EC'\">ml64",
    "-D_M_ARM64EC",
    "<ExcludedFromBuild Condition=\"'$(Configuration)|$(Platform)'=='SbieRelease|ARM64EC'\">false</ExcludedFromBuild>",
    "<ExcludedFromBuild Condition=\"'$(Configuration)|$(Platform)'=='SbieDebug|ARM64EC'\">false</ExcludedFromBuild>",
]:
    require(vcxproj, term, "SboxDll ARM64EC assembly build")

for term in [
    "*ip.pL++ = 0x580000b1;\t// ldr x17, 20 - NewDetour",
    "*ip.pL++ = 0x58000050;\t// ldr x16, 8 - ApiInstrumentationAsm",
    "*ip.pL++ = 0xD61F0200;\t// br x16",
    "*ip.pQ++ = (ULONG_PTR)ApiInstrumentationAsm;",
    "*ip.pQ++ = (ULONG_PTR)NewDetour;",
]:
    require(dllhook, term, "dllhook API trace detour")

for term in [
    "void ApiInstrumentation(const char* pName, void** pStack)",
    "void* ReturnAddress = *(pStack - 1);",
    "SbieApi_MonitorPut2Ex(MONITOR_APICALL | MONITOR_TRACE",
]:
    require(trace, term, "trace ApiInstrumentation consumer")

for term in [
    "ULONG_PTR RpcRt_NdrClientCall2ARM64(",
    "void* ReturnAddress = *(pStack - 4);",
    "Secure_CheckElevation((struct SECURE_UAC_ARGS*)pStack)",
]:
    require(rpcrt, term, "RPC ARM64EC wrapper consumer")

for term in [
    "first four registers are used for",
    "x4` points at the first stack parameter",
    "x5` carries the stack-parameter byte size",
    "non-variadic",
    "x0-x7",
]:
    require(spec, term, "spec ABI reasoning")

for term in [
    "### SREV-177: ARM64EC API Instrumentation Argument Preservation",
    "ARM64EC_API_INSTRUMENTATION_ARGUMENT_PRESERVATION",
    "srev-177-arm64ec-api-instrumentation-argument-preservation.schema.json",
    "Sandboxie/core/dll/util_EC.asm",
    "ApiInstrumentationAsm",
    "Windows ARM64EC",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-177 schema/source gate passed")
