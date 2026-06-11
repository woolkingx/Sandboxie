#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-149 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-149 failed: {label} still contains {needle!r}")


def between(text: str, start: str, end: str) -> str:
    a = text.index(start)
    b = text.index(end, a + len(start))
    return text[a:b]


schema = json.loads(
    (ROOT / "docs/plan/srev-149-kernel-time-hook-output-gate.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-149 failed: schema is not draft-07")
if schema.get("id") != "KERNEL_TIME_HOOK_OUTPUT_GATE":
    raise SystemExit("SREV-149 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "UseChangeSpeed time hooks may transform only a successful real API output",
    "A failed real API call must propagate the failure return without writing the output pointer in Sandboxie's hook",
    "QueryUnbiasedInterruptTime reports failure when called with a null pointer; the hook must not dereference that pointer after failure",
    "Fractional configured speed ratios must preserve multiply-before-divide arithmetic: value * AddTickSpeed / LowTickSpeed",
    "Zero AddTickSpeed or zero LowTickSpeed follows the existing local fallback branch and is not redefined by this SREV",
]:
    require(contracts, term, "schema")

src = (ROOT / "Sandboxie/core/dll/kernel.c").read_text()
settings = (ROOT / "Sandboxie/install/SbieSettings.ini").read_text()
spec = (ROOT / "docs/plan/srev-149-kernel-time-hook-output-gate.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-149.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "[UseChangeSpeed]",
    "[AddTickSpeed]",
    "[LowTickSpeed]",
    "Requirements=<UseChangeSpeed=y>",
    "Syntax=[sn]=zero or positive integer",
]:
    require(settings, term, "settings evidence")

unbiased = between(
    src,
    "_FX BOOL Kernel_QueryUnbiasedInterruptTime(PULONGLONG UnbiasedTime)",
    "//---------------------------------------------------------------------------\n// Kernel_SleepEx",
)
for term in [
    "BOOL rtn = __sys_QueryUnbiasedInterruptTime(UnbiasedTime);",
    "if (!rtn || !UnbiasedTime)",
    "return rtn;",
    "*UnbiasedTime = *UnbiasedTime * add / low;",
    "*UnbiasedTime *= add;",
]:
    require(unbiased, term, "Kernel_QueryUnbiasedInterruptTime")
reject(unbiased, "*UnbiasedTime *= add / low;", "Kernel_QueryUnbiasedInterruptTime")
if not (
    unbiased.index("BOOL rtn = __sys_QueryUnbiasedInterruptTime(UnbiasedTime);")
    < unbiased.index("if (!rtn || !UnbiasedTime)")
    < unbiased.index("ULONG add = SbieApi_QueryConfNumber(NULL, L\"AddTickSpeed\", 1);")
    < unbiased.index("*UnbiasedTime = *UnbiasedTime * add / low;")
):
    raise SystemExit("SREV-149 failed: unbiased time gate/order is wrong")

qpc = between(
    src,
    "_FX BOOL Kernel_QueryPerformanceCounter(LARGE_INTEGER* lpPerformanceCount)",
    "//---------------------------------------------------------------------------\n// Kernel_GetUserDefaultUILanguage",
)
for term in [
    "BOOL rtn = __sys_QueryPerformanceCounter(lpPerformanceCount);",
    "if (!rtn || !lpPerformanceCount)",
    "return rtn;",
    "lpPerformanceCount->QuadPart = lpPerformanceCount->QuadPart * add / low;",
]:
    require(qpc, term, "Kernel_QueryPerformanceCounter")
if not (
    qpc.index("BOOL rtn = __sys_QueryPerformanceCounter(lpPerformanceCount);")
    < qpc.index("if (!rtn || !lpPerformanceCount)")
    < qpc.index("ULONG add = SbieApi_QueryConfNumber(NULL, L\"AddTickSpeed\", 1);")
    < qpc.index("lpPerformanceCount->QuadPart = lpPerformanceCount->QuadPart * add / low;")
):
    raise SystemExit("SREV-149 failed: performance counter gate/order is wrong")

for term in [
    "Sandboxie/core/dll/kernel.c",
    "Sandboxie/install/SbieSettings.ini",
    "### SREV-149: Kernel Time Hook Output Gate",
    "KERNEL_TIME_HOOK_OUTPUT_GATE",
    "srev-149-kernel-time-hook-output-gate.schema.json",
    "QueryUnbiasedInterruptTime",
    "QueryPerformanceCounter",
    "UseChangeSpeed",
    "multiply-before-divide",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-149 schema/source gate passed")
