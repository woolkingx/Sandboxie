#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-036 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-036 failed: {label} still contains {needle!r}")


schema = json.loads((ROOT / "docs/plan/srev-036-conf-user-name-wire.schema.json").read_text())
if schema.get("id") != "CONF_SET_USER_NAME_COUNTED_STRING":
    raise SystemExit("SREV-036 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "UNICODE_STRING64.Length is a byte count",
    "UNICODE_STRING64.Length must be nonzero, <= 1024, and <= MaximumLength",
    "embedded NUL is invalid",
    "CONF_USER.sid_len and CONF_USER.name_len are WCHAR counts",
    "CONF_USER.name storage starts after the full counted sidstring",
    "service-side sender validates sidstring as a string SID",
]:
    require(contracts, term, "schema")

src = (ROOT / "Sandboxie/core/drv/conf_user.c").read_text()
svc = (ROOT / "Sandboxie/core/svc/DriverAssist.cpp").read_text()
spec = (ROOT / "docs/plan/srev-036-conf-user-name-wire.md").read_text()
ledger = read_combined_ledger(ROOT)

start = src.index("NTSTATUS Conf_Api_SetUserName(")
end = src.index("// Conf_Api_IsBoxEnabled", start)
set_user = src[start:end]

for term in [
    "static BOOLEAN Conf_Api_SetUserNameContainsWChar(",
    "ULONG count = byte_len / sizeof(WCHAR);",
    "if (text[i] == ch)",
]:
    require(src, term, "counted WCHAR helper")

for term in [
    "user_sid_len = user_uni->Length;",
    "(user_sid_len & (sizeof(WCHAR) - 1))",
    "(user_uni->MaximumLength < user_sid_len)",
    "user_name_len = user_uni->Length;",
    "(user_name_len & (sizeof(WCHAR) - 1))",
    "(user_uni->MaximumLength < user_name_len)",
    "Conf_Api_SetUserNameContainsWChar(user->sid, user_sid_len, L'\\0')",
    "user->sid_len = user_sid_len / sizeof(WCHAR);",
    "user->name = user->sid + user->sid_len + 1;",
    "Conf_Api_SetUserNameContainsWChar(user->name, user_name_len, L'\\0')",
    "user->name_len = user_name_len / sizeof(WCHAR);",
]:
    require(set_user, term, "Conf_Api_SetUserName")

reject(set_user, "user_uni->Length & ~1", "Conf_Api_SetUserName")
reject(set_user, "user->sid_len = wcslen(user->sid);", "Conf_Api_SetUserName")
reject(set_user, "user->name_len = wcslen(user->name);", "Conf_Api_SetUserName")

for term in [
    "ConvertStringSidToSid(msg->sid_string, &pSid)",
    "SbieApi_SetUserName(msg->sid_string, username)",
]:
    require(svc, term, "DriverAssist sender")

for term in [
    "https://learn.microsoft.com/en-us/windows/win32/api/ntdef/ns-ntdef-_unicode_string",
    "https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-probeforread",
    "https://learn.microsoft.com/en-us/windows/win32/api/sddl/nf-sddl-convertstringsidtosidw",
    "https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-lookupaccountsida",
    "srev-036-conf-user-name-wire.schema.json",
]:
    require(spec, term, "spec")

for term in [
    "### SREV-036: Config User Name Counted String",
    "Conf_Api_SetUserNameContainsWChar",
    "srev-036-conf-user-name-wire.schema.json",
]:
    require(ledger, term, "ledger")

print("SREV-036 schema/source gate passed")
