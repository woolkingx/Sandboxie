#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-040 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-040 failed: {label} still contains {needle!r}")


schema = json.loads((ROOT / "docs/plan/srev-040-is-box-enabled-sid-string.schema.json").read_text())
if schema.get("id") != "API_IS_BOX_ENABLED_SID_STRING":
    raise SystemExit("SREV-040 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "must be copied before Conf_IsBoxEnabled reads it",
    "readable as 96 WCHARs",
    "NUL terminator before the local 94-WCHAR payload cap",
    "empty sid_string is invalid",
    "must start with S-",
    "kernel-owned SID strings",
]:
    require(contracts, term, "schema")

api = (ROOT / "Sandboxie/core/drv/api.c").read_text()
conf_user = (ROOT / "Sandboxie/core/drv/conf_user.c").read_text()
spec = (ROOT / "docs/plan/srev-040-is-box-enabled-sid-string.md").read_text()
ledger = read_combined_ledger(ROOT)

api_start = api.index("_FX BOOLEAN Api_CopySidStringFromUser(")
api_end = api.index("// Api_CopyStringToUser", api_start)
sid_copy = api[api_start:api_end]

for term in [
    "ULONG i;",
    "if (! user_sidstring)",
    "ProbeForRead(\n        (WCHAR *)user_sidstring, sizeof(WCHAR) * 96, sizeof(WCHAR));",
    "for (i = 0; i < 94; ++i)",
    "if (user_sidstring[i] == L'\\0')",
    "sidstring96[i] = user_sidstring[i];",
    "if ((! i) || (i == 94))",
    "sidstring96[0] == L'S' && sidstring96[1] == L'-'",
]:
    require(sid_copy, term, "Api_CopySidStringFromUser")

reject(sid_copy, "wcsncpy(sidstring96, user_sidstring, 94)", "Api_CopySidStringFromUser")
reject(sid_copy, "sizeof(UCHAR)", "Api_CopySidStringFromUser")

conf_start = conf_user.index("_FX NTSTATUS Conf_Api_IsBoxEnabled(")
conf_end = conf_user.index("\n}", conf_start) + 2
is_enabled = conf_user[conf_start:conf_end]

for term in [
    "WCHAR sidstring[96];",
    "if (! Api_CopySidStringFromUser(sidstring, args->sid_string.val))",
    "return STATUS_INVALID_PARAMETER;",
    "sid = sidstring;",
    "Process_GetSidStringAndSessionId(",
]:
    require(is_enabled, term, "Conf_Api_IsBoxEnabled")

reject(is_enabled, "sid = args->sid_string.val;", "Conf_Api_IsBoxEnabled")

for term in [
    "https://learn.microsoft.com/en-us/windows/win32/api/sddl/nf-sddl-convertstringsidtosidw",
    "https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-probeforread",
    "srev-040-is-box-enabled-sid-string.schema.json",
]:
    require(spec, term, "spec")

for term in [
    "### SREV-040: IsBoxEnabled SID String Boundary",
    "Api_CopySidStringFromUser",
    "srev-040-is-box-enabled-sid-string.schema.json",
]:
    require(ledger, term, "ledger")

print("SREV-040 schema/source gate passed")
