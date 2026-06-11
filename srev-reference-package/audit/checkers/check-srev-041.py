#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-041 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-041 failed: {label} still contains {needle!r}")


schema = json.loads((ROOT / "docs/plan/srev-041-api-copy-box-name.schema.json").read_text())
if schema.get("id") != "API_COPY_BOX_NAME_FIXED_STRING":
    raise SystemExit("SREV-041 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "must be copied before Box_IsValidName reads it",
    "BOXNAME_COUNT - 2 WCHARs",
    "NUL terminator before the BOXNAME_COUNT - 2 payload cap",
    "empty box name is invalid",
    "must not be truncated",
    "Box_IsValidName",
]:
    require(contracts, term, "schema")

api = (ROOT / "Sandboxie/core/drv/api.c").read_text()
process_api = (ROOT / "Sandboxie/core/drv/process_api.c").read_text()
conf_user = (ROOT / "Sandboxie/core/drv/conf_user.c").read_text()
spec = (ROOT / "docs/plan/srev-041-api-copy-box-name.md").read_text()
ledger = read_combined_ledger(ROOT)

start = api.index("_FX BOOLEAN Api_CopyBoxNameFromUser(")
end = api.index("// Api_CopySidStringFromUser", start)
copy = api[start:end]

for term in [
    "ULONG i;",
    "if (! user_boxname)",
    "sizeof(WCHAR) * (BOXNAME_COUNT - 2),\n                 sizeof(WCHAR));",
    "for (i = 0; i < (BOXNAME_COUNT - 2); ++i)",
    "if (user_boxname[i] == L'\\0')",
    "boxname34[i] = user_boxname[i];",
    "if ((! i) || (i == (BOXNAME_COUNT - 2)))",
    "Box_IsValidName(boxname34)",
]:
    require(copy, term, "Api_CopyBoxNameFromUser")

reject(copy, "wcsncpy(boxname34, user_boxname", "Api_CopyBoxNameFromUser")
reject(copy, "sizeof(UCHAR)", "Api_CopyBoxNameFromUser")

for term in [
    "Api_CopyBoxNameFromUser(boxname, (WCHAR *)user_box_parm)",
    "Api_CopyBoxNameFromUser(\n            boxname, (WCHAR *)args->box_name.val)",
]:
    require(process_api, term, "process callers")

require(conf_user, "Api_CopyBoxNameFromUser(boxname, (WCHAR *)args->box_name.val)", "Conf_Api_IsBoxEnabled caller")

for term in [
    "https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-probeforread",
    "srev-041-api-copy-box-name.schema.json",
]:
    require(spec, term, "spec")

for term in [
    "### SREV-041: API Copy Box Name Fixed String",
    "Api_CopyBoxNameFromUser",
    "srev-041-api-copy-box-name.schema.json",
]:
    require(ledger, term, "ledger")

print("SREV-041 schema/source gate passed")
