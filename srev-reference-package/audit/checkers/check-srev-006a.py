#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-006A failed: {label} missing {needle!r}")


def assert_before(text: str, label: str, earlier: str, later: str) -> None:
    e = text.find(earlier)
    l = text.find(later)
    if e < 0 or l < 0 or e > l:
        raise SystemExit(f"SREV-006A failed: {label}")


schema = json.loads((ROOT / "docs/plan/srev-006a-ini-fixed-string-spec.schema.json").read_text())
if schema.get("id") != "SBIEINI_FIXED_STRING_SHAPE":
    raise SystemExit("SREV-006A failed: schema missing SBIEINI_FIXED_STRING_SHAPE")

contracts = "\n".join(schema["contracts"])
for term in [
    "Fixed WCHAR[66] inline strings must contain a L'\\0'",
    "SbieIni_HasTerminator is the only legal way",
    "CheckSettingStrings calls SbieIni_HasTerminator on password, section, setting",
]:
    require(contracts, term, "schema contracts")

src = (ROOT / "Sandboxie/core/svc/sbieiniserver.cpp").read_text()
spec = (ROOT / "docs/plan/srev-006a-ini-fixed-string-spec.md").read_text()
ledger = read_combined_ledger(ROOT)

for term in [
    "SbieIni_HasTerminator",
    "ARRAYSIZE(req->password)",
    "ARRAYSIZE(req->section)",
    "ARRAYSIZE(req->setting)",
    "ARRAYSIZE(req->varname)",
    "ARRAYSIZE(req->old_password)",
    "ARRAYSIZE(req->new_password)",
    "available < sizeof(WCHAR)",
    "available - sizeof(WCHAR)",
    "MSGID_SBIE_INI_SET_PASSWORD",
]:
    require(src, term, "service source")

assert_before(src, "CheckRequest string gate before authorization",
              "SbieIni_CheckSettingStrings(req)",
              "IsCallerAuthorized(hToken, req->password, req->section)")
assert_before(src, "GetSetting section gate before GetValue",
              "SbieIni_HasTerminator(req->section",
              "m_pSbieIni->GetValue(req->section, req->setting")
assert_before(src, "Template varname gate before wcslen",
              "SbieIni_HasTerminator(req->varname",
              "wcslen(req->varname)")
assert_before(src, "Password old gate before authorization",
              "SbieIni_HasTerminator(req->old_password",
              "IsCallerAuthorized(hToken, req->old_password)")
assert_before(src, "SetDat setting gate before wcsrchr",
              "SbieIni_HasTerminator(req->setting",
              "wcsrchr(req->setting")

for term in ["null-terminated", "SBIE_INI_SETTING_REQ.password", "SCM service-name"]:
    require(spec, term, "spec")

require(ledger, "### SREV-006: Broker Request Fixed Strings Are Used Before NUL-Terminator Proof", "ledger")
require(ledger, "Sandboxie/core/svc/sbieiniserver.cpp", "ledger")

print("SREV-006A schema/source gate passed")
