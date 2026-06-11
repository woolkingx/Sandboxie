#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-080 failed: {label} missing {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-080-userenv-verify-version-info.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-080 failed: schema is not draft-07")
if schema.get("id") != "USERENV_VERIFY_VERSION_INFO_OVERRIDE":
    raise SystemExit("SREV-080 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "documented VerifyVersionInfoW is the public boundary",
    "VerSetConditionMask and does not hardcode bit layout",
    "OverrideOsBuild changes only major, minor, build, and service-pack fields",
    "ERROR_OLD_WIN_VERSION",
    "ERROR_INVALID_PARAMETER",
]:
    require(contracts, term, "schema")

src = (ROOT / "Sandboxie/core/dll/userenv.c").read_text()
spec = (ROOT / "docs/plan/srev-080-userenv-verify-version-info.md").read_text()
ledger = read_combined_ledger(ROOT)

for term in [
    "typedef BOOL (*P_VerifyVersionInfoW)",
    "typedef ULONGLONG (WINAPI *P_VerSetConditionMask)",
    "static P_VerifyVersionInfoW         __sys_VerifyVersionInfoW",
    "static P_VerSetConditionMask        __sys_VerSetConditionMask",
    "VerifyVersionInfoW = GetProcAddress(module, \"VerifyVersionInfoW\");",
    "GetProcAddress(module, \"VerSetConditionMask\")",
    "SbieDll_Hook(\"VerifyVersionInfoW\", VerifyVersionInfoW,",
    "UserEnv_VerifyVersionInfoW, module)",
]:
    require(src, term, "source hook")

if "RtlSwitchedVVI" in src:
    raise SystemExit("SREV-080 failed: private RtlSwitchedVVI TODO still present")

start = src.index("static BOOLEAN UserEnv_GetVersionCondition(")
end = src.index("_FX BOOL UserEnv_VerifyVersionInfoW(", start)
helpers = src[start:end]
for term in [
    "__sys_VerSetConditionMask(0, TypeMask, i)",
    "ConditionMask &= fieldMask;",
    "UserEnv_IsVersionValueCondition",
    "UserEnv_CompareVersionSuite",
    "UserEnv_VerifyVersionNumbers",
]:
    require(helpers, term, "condition helper")

for forbidden in [
    "VER_NUM_BITS_PER_CONDITION_MASK",
    "VER_CONDITION_MASK",
    "<<",
]:
    if forbidden in helpers:
        raise SystemExit(
            f"SREV-080 failed: condition helper appears to hardcode mask layout: {forbidden}"
        )

func = src[end:]
for term in [
    "if (!UserEnv_dwBuildNumber || !__sys_VerSetConditionMask)",
    "return __sys_VerifyVersionInfoW(",
    "lpVersionInformation->dwOSVersionInfoSize !=",
    "sizeof(OSVERSIONINFOEXW)",
    "SupportedTypeMask",
    "status = __sys_RtlGetVersion(&CurrentVersion);",
    "UserEnv_MkVersionEx(",
    "SetLastError(ERROR_INVALID_PARAMETER);",
    "SetLastError(ERROR_OLD_WIN_VERSION);",
    "VER_PLATFORMID",
    "VER_PRODUCT_TYPE",
    "VER_SUITENAME",
]:
    require(func, term, "VerifyVersionInfoW source")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "### SREV-080: UserEnv VerifyVersionInfo Override Contract",
    "USERENV_VERIFY_VERSION_INFO_OVERRIDE",
    "srev-080-userenv-verify-version-info.schema.json",
]:
    require(ledger, term, "ledger")

print("SREV-080 schema/source gate passed")
