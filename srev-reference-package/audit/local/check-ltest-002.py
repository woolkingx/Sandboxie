#!/usr/bin/env python3
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
LOCAL = ROOT / "docs/plan/local"


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"LTEST-002 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"LTEST-002 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (LOCAL / "ltest-002-sandman-test-ui-certificate-gate.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("LTEST-002 failed: schema is not draft-07")
if schema.get("id") != "SANDMAN_TEST_UI_CERTIFICATE_GATE":
    raise SystemExit("LTEST-002 failed: wrong schema id")
if schema.get("owner") != "SandboxiePlus/SandMan/SandMan.cpp":
    raise SystemExit("LTEST-002 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "Test=true is a local SandMan UI test setting",
    "not a supporter certificate",
    "the setting is read from Sandboxie.ini GlobalSettings Test",
    "accepted true spellings are true yes y 1 and on",
    "CSandMan::CheckCertificate returns true",
    "before showing the supporter-certificate QMessageBox",
    "must not mutate g_CertInfo",
    "must not change driver feature flags or core process enforcement",
    "not an SREV",
]:
    require(contracts, term, "schema contract")

sandman = (ROOT / "SandboxiePlus/SandMan/SandMan.cpp").read_text()
spec = (LOCAL / "ltest-002-sandman-test-ui-certificate-gate.md").read_text()
ledger_fragment = (LOCAL / "ltest-002.md").read_text()

helper_start = sandman.index("static bool CSandMan_IsLocalTestMode()")
helper_end = sandman.index("bool CSandMan::CheckCertificate", helper_start)
helper = sandman[helper_start:helper_end]

for term in [
    'theAPI->SbieIniGet("GlobalSettings", "Test", 0)',
    ".trimmed().toLower()",
    'value == "true"',
    'value == "yes"',
    'value == "y"',
    'value == "1"',
    'value == "on"',
]:
    require(helper, term, "CSandMan_IsLocalTestMode source")

check_start = sandman.index("bool CSandMan::CheckCertificate")
check_end = sandman.index("void InitCertSlot();", check_start)
check = sandman[check_start:check_end]

for term in [
    "if (CSandMan_IsLocalTestMode())",
    "return true;",
    "QMessageBox msgBox(pWidget);",
]:
    require(check, term, "CheckCertificate source")
if check.index("if (CSandMan_IsLocalTestMode())") > check.index("QMessageBox msgBox(pWidget);"):
    raise SystemExit("LTEST-002 failed: local UI gate must run before QMessageBox")

for stale in [
    "g_CertInfo.active = 1",
    "g_CertInfo.opt_sec = 1",
    "g_CertInfo.opt_enc = 1",
    "g_CertInfo.opt_net = 1",
]:
    reject(helper + check, stale, "g_CertInfo mutation")

for term in [
    "SANDMAN_TEST_UI_CERTIFICATE_GATE",
    "Test=true",
    "not a supporter certificate",
    "local-only scaffolding",
    "does not mutate `g_CertInfo`",
    "Windows UI/runtime proof remains",
    "not an SREV",
]:
    require(spec, term, "spec")

for term in [
    "kind: local-test-entry",
    "id: LTEST-002",
    "owner: SandboxiePlus/SandMan/SandMan.cpp",
    "spec: docs/plan/local/ltest-002-sandman-test-ui-certificate-gate.md",
    "schema: docs/plan/local/ltest-002-sandman-test-ui-certificate-gate.schema.json",
    "checker: docs/plan/local/check-ltest-002.py",
]:
    require(ledger_fragment, term, "ledger fragment header")

for term in [
    "### LTEST-002: SandMan Test UI Certificate Gate",
    "SANDMAN_TEST_UI_CERTIFICATE_GATE",
    "`Test=true`",
    "`CSandMan_IsLocalTestMode`",
    "`CSandMan::CheckCertificate`",
    "`g_CertInfo`",
    "`QMessageBox`",
]:
    require(ledger_fragment, term, "local ledger")

print("LTEST-002 schema/source gate passed")
