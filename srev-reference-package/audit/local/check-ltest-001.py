#!/usr/bin/env python3
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
LOCAL = ROOT / "docs/plan/local"


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"LTEST-001 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"LTEST-001 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (LOCAL / "ltest-001-sandboxie-test-parameter-verification-gate.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("LTEST-001 failed: schema is not draft-07")
if schema.get("id") != "SANDBOXIE_TEST_PARAMETER_VERIFICATION_GATE":
    raise SystemExit("LTEST-001 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/drv/util.c":
    raise SystemExit("LTEST-001 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "Test=true is a local Sandboxie runtime setting",
    "not a Windows loader signing control",
    "MyIsTestMode is the single kernel helper",
    "accepted true spellings are true yes y 1 and on",
    "MyIsCallerSigned treats Test=true",
    "Process_Create treats Test=true",
    "Api_QueryDriverInfo projects Test=true",
    "must not mutate Verify_CertInfo",
    "must not change DynData parsing or Windows driver load policy",
]:
    require(contracts, term, "schema contract")

util = (ROOT / "Sandboxie/core/drv/util.c").read_text()
util_h = (ROOT / "Sandboxie/core/drv/util.h").read_text()
process = (ROOT / "Sandboxie/core/drv/process.c").read_text()
api = (ROOT / "Sandboxie/core/drv/api.c").read_text()
spec = (LOCAL / "ltest-001-sandboxie-test-parameter-verification-gate.md").read_text()
ledger_fragment = (LOCAL / "ltest-001.md").read_text()

require(util, '#include "conf.h"', "config owner include")
require(util_h, "BOOLEAN MyIsTestMode(void);", "helper declaration")

start = util.index("_FX BOOLEAN MyIsTestMode(void)")
end = util.index("_FX BOOLEAN MyIsCallerSigned(void)", start)
helper = util[start:end]

for term in [
    'Conf_Get(NULL, L"Test", 0)',
    '_wcsicmp(value, L"true") == 0',
    '_wcsicmp(value, L"yes") == 0',
    '_wcsicmp(value, L"y") == 0',
    '_wcsicmp(value, L"1") == 0',
    '_wcsicmp(value, L"on") == 0',
    "Conf_AdjustUseCount(TRUE);",
    "Conf_AdjustUseCount(FALSE);",
]:
    require(helper, term, "MyIsTestMode source")

caller_start = util.index("_FX BOOLEAN MyIsCallerSigned(void)")
caller = util[caller_start:caller_start + 700]
for term in [
    "Test=true is a local Sandboxie test gate",
    "if (MyIsTestMode())",
    "return TRUE;",
    "if (Driver_OsTestSigning)",
]:
    require(caller, term, "MyIsCallerSigned source")
if caller.index("if (MyIsTestMode())") > caller.index("if (Driver_OsTestSigning)"):
    raise SystemExit("LTEST-001 failed: Test=true gate must be explicit before TESTSIGNING fallback")

for term in [
    "BOOLEAN test_mode = MyIsTestMode();",
    "test_mode || (Verify_CertInfo.active && Verify_CertInfo.opt_sec)",
    "test_mode || (Verify_CertInfo.active && Verify_CertInfo.opt_enc)",
]:
    require(process, term, "Process_Create source")

for term in [
    "BOOLEAN test_mode = MyIsTestMode();",
    "test_mode || Verify_CertInfo.active",
    "test_mode || Verify_CertInfo.opt_sec",
    "test_mode || Verify_CertInfo.opt_enc",
    "test_mode || Verify_CertInfo.opt_net",
    "test_mode || Verify_CertInfo.type == eCertDeveloper",
]:
    require(api, term, "Api_QueryDriverInfo source")

for stale in [
    "Verify_CertInfo.active = 1",
    "Verify_CertInfo.opt_sec = 1",
    "Verify_CertInfo.opt_enc = 1",
    "Verify_CertInfo.opt_net = 1",
]:
    reject(util + process + api, stale, "Verify_CertInfo mutation")

for term in [
    "SANDBOXIE_TEST_PARAMETER_VERIFICATION_GATE",
    "Test=true",
    "not a Windows loader signing control",
    "single kernel helper",
    "non-mutation of `Verify_CertInfo`",
    "Windows build and runtime proof remain required",
    "not an SREV",
]:
    require(spec, term, "spec")

for term in [
    "kind: local-test-entry",
    "id: LTEST-001",
    "owner: Sandboxie/core/drv/util.c",
    "spec: docs/plan/local/ltest-001-sandboxie-test-parameter-verification-gate.md",
    "schema: docs/plan/local/ltest-001-sandboxie-test-parameter-verification-gate.schema.json",
    "checker: docs/plan/local/check-ltest-001.py",
]:
    require(ledger_fragment, term, "ledger fragment header")

for term in [
    "### LTEST-001: Sandboxie Test Parameter Verification Gate",
    "SANDBOXIE_TEST_PARAMETER_VERIFICATION_GATE",
    "`Test=true`",
    "`MyIsTestMode`",
    "`MyIsCallerSigned`",
    "`Process_Create`",
    "`Api_QueryDriverInfo`",
]:
    require(ledger_fragment, term, "local ledger")

print("LTEST-001 schema/source gate passed")
