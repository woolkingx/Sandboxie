#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-039 failed: {label} missing {needle!r}")


schema = json.loads((ROOT / "docs/plan/srev-039-api-copy-string-to-user.schema.json").read_text())
if schema.get("id") != "API_COPY_STRING_TO_USER_COUNTED_STRING":
    raise SystemExit("SREV-039 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "len is a byte count",
    "nonzero len must be at least sizeof(WCHAR)",
    "UNICODE_STRING64.MaximumLength is a byte count",
    "nonzero len requires a non-NULL user Buffer",
    "len must be <= MaximumLength",
    "Length is set to len - sizeof(WCHAR)",
]:
    require(contracts, term, "schema")

src = (ROOT / "Sandboxie/core/drv/api.c").read_text()
process_api = (ROOT / "Sandboxie/core/drv/process_api.c").read_text()
conf = (ROOT / "Sandboxie/core/drv/conf.c").read_text()
spec = (ROOT / "docs/plan/srev-039-api-copy-string-to-user.md").read_text()
ledger = read_combined_ledger(ROOT)

start = src.index("_FX void Api_CopyStringToUser(")
end = src.index("// Api_CopyStringFromUser", start)
copy = src[start:end]

for term in [
    "if (len & (sizeof(WCHAR) - 1))",
    "ExRaiseStatus(STATUS_INVALID_PARAMETER);",
    "if (len && (len < sizeof(WCHAR) || (! str)))",
    "if (uni->MaximumLength & (sizeof(WCHAR) - 1))",
    "if (len > uni->MaximumLength)",
    "ExRaiseStatus(STATUS_BUFFER_TOO_SMALL);",
    "if (len && (! buf))",
    "ProbeForWrite(buf, len, sizeof(WCHAR));",
    "uni->Length = (USHORT)len - sizeof(WCHAR);",
]:
    require(copy, term, "Api_CopyStringToUser")

for term in [
    "Api_CopyStringToUser(\n            (UNICODE_STRING64 *)parms[2]",
    "Api_CopyStringToUser(file_path, box->file_path, box->file_path_len);",
    "Api_CopyStringToUser(file_path, proc->box->file_raw_path, proc->box->file_raw_path_len);",
]:
    require(process_api, term, "process callers")

require(src, "Api_CopyStringToUser(user_uni, ptr, len);", "Api_GetHomePath caller")
require(conf, "Api_CopyStringToUser(user_uni, value2, len);", "Conf_Api_Query caller")

for term in [
    "https://learn.microsoft.com/en-us/windows/win32/api/ntdef/ns-ntdef-_unicode_string",
    "https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-probeforwrite",
    "srev-039-api-copy-string-to-user.schema.json",
]:
    require(spec, term, "spec")

for term in [
    "### SREV-039: API Copy String To User Counted String",
    "Api_CopyStringToUser",
    "srev-039-api-copy-string-to-user.schema.json",
]:
    require(ledger, term, "ledger")

print("SREV-039 schema/source gate passed")
