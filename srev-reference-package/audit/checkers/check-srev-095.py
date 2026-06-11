#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-095 failed: {label} missing {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-095-arm64-api-instrumentation-abi.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-095 failed: schema is not draft-07")
if schema.get("id") != "ARM64_API_INSTRUMENTATION_ABI":
    raise SystemExit("SREV-095 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "x17 pointing at the trace entry header",
    "preserves x0-x7 before calling ApiInstrumentation",
    "passes pName in x0 and the saved argument frame in x1",
    "saved argument frame begins at the saved x0/x1 pair",
    "pArgs[-1] is the saved LR",
    "preserves x16/x17 across the call",
    "keeps SP 16-byte aligned",
    "does not change ApiTrace runtime behavior",
]:
    require(contracts, term, "schema")

util_arm = (ROOT / "Sandboxie/core/dll/util_arm.asm").read_text()
dllhook = (ROOT / "Sandboxie/core/dll/dllhook.c").read_text()
trace = (ROOT / "Sandboxie/core/dll/trace.c").read_text()
spec = (ROOT / "docs/plan/srev-095-arm64-api-instrumentation-abi.md").read_text()
ledger = read_combined_ledger(ROOT)

for term in [
    "ApiInstrumentationProxy",
    "ApiInstrumentationAsm PROC",
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
    "ldr     x16, [x17]",
    "br      x16",
]:
    require(util_arm, term, "util_arm.asm ARM64 API instrumentation ABI")

if "; todo" in util_arm:
    raise SystemExit("SREV-095 failed: stale util_arm TODO remains")
if "; InstrumentationCallbackAsm\n;----------------------------------------------------------------------------\n\n\nApiInstrumentationAsm PROC" in util_arm:
    raise SystemExit("SREV-095 failed: stale ApiInstrumentation heading remains")

for term in [
    "*ip.pL++ = 0x580000b1;\t// ldr x17, 20 - NewDetour",
    "*ip.pL++ = 0x58000050;\t// ldr x16, 8 - ApiInstrumentationAsm",
    "*ip.pL++ = 0xD61F0200;\t// br x16",
    "*ip.pQ++ = (ULONG_PTR)ApiInstrumentationAsm;",
    "*ip.pQ++ = (ULONG_PTR)NewDetour;",
    "FlushInstructionCache(GetCurrentProcess(), pTrace->code, 32);",
]:
    require(dllhook, term, "dllhook.c ARM64 trace detour")

for term in [
    "void ApiInstrumentation(const char* pName, void** pStack)",
    "void* ReturnAddress = *(pStack - 1);",
    "ReservedForDebuggerInstrumentation[15]",
    "SbieApi_MonitorPut2Ex(MONITOR_APICALL | MONITOR_TRACE",
]:
    require(trace, term, "trace.c ApiInstrumentation consumer")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "x0-x8` as volatile",
    "x16-x17` as volatile intra-procedure-call",
    "stack as always 16-byte aligned",
    "No runtime behavior was changed.",
]:
    require(spec, term, "spec ABI classification")

for term in [
    "### SREV-095: ARM64 API Instrumentation ABI",
    "ARM64_API_INSTRUMENTATION_ABI",
    "srev-095-arm64-api-instrumentation-abi.schema.json",
]:
    require(ledger, term, "ledger")

print("SREV-095 schema/source gate passed")
