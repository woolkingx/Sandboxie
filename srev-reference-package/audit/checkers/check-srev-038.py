#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-038 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-038 failed: {label} still contains {needle!r}")


schema = json.loads((ROOT / "docs/plan/srev-038-api-copy-string-from-user.schema.json").read_text())
if schema.get("id") != "API_COPY_STRING_FROM_USER_COUNTED_STRING":
    raise SystemExit("SREV-038 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "UNICODE_STRING64.Length is a byte count",
    "UNICODE_STRING64.Length must be <= MaximumLength",
    "nonzero Length requires a non-NULL Buffer",
    "locally NUL-terminated",
    "embedded NUL in the counted payload is invalid",
    "allocation failure returns STATUS_INSUFFICIENT_RESOURCES",
]:
    require(contracts, term, "schema")

src = (ROOT / "Sandboxie/core/drv/api.c").read_text()
conf = (ROOT / "Sandboxie/core/drv/conf.c").read_text()
spec = (ROOT / "docs/plan/srev-038-api-copy-string-from-user.md").read_text()
ledger = read_combined_ledger(ROOT)

start = src.index("_FX NTSTATUS Api_CopyStringFromUser(")
end = src.index("// Api_ProcessExemptionControl", start)
copy = src[start:end]

for term in [
    "static BOOLEAN Api_ContainsWChar(",
]:
    require(src, term, "Api_CopyStringFromUser helper")

for term in [
    "if (uni->Length & (sizeof(WCHAR) - 1))",
    "if (uni->Length > uni->MaximumLength)",
    "if (uni->Length && (! buff))",
    "if (uni->Length)\n\t\t\tmemcpy(*str, buff, uni->Length);",
    "Api_ContainsWChar(*str, uni->Length, L'\\0')",
    "Mem_Free(*str, *len);",
    "*str = NULL;",
    "*len = 0;",
    "(*str)[uni->Length / sizeof(WCHAR)] = L'\\0';",
]:
    require(copy, term, "Api_CopyStringFromUser")

for term in [
    "ProbeForRead(buff, *len",
    "memcpy(*str, buff, *len)",
    "(*str)[*len / sizeof(WCHAR)]",
]:
    reject(copy, term, "Api_CopyStringFromUser")

for term in [
    "status = Api_CopyStringFromUser(&value_ptr, &value_len, (UNICODE_STRING64*)parms[4]);",
    "Conf_Update(&Conf_Data, section_name, setting_name, value_ptr, uMode)",
]:
    require(conf, term, "Conf_Api_Update caller")

for term in [
    "https://learn.microsoft.com/en-us/windows/win32/api/ntdef/ns-ntdef-_unicode_string",
    "https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-probeforread",
    "one WCHAR past the",
    "srev-038-api-copy-string-from-user.schema.json",
]:
    require(spec, term, "spec")

for term in [
    "### SREV-038: API Copy String From User Counted String",
    "Api_CopyStringFromUser",
    "srev-038-api-copy-string-from-user.schema.json",
]:
    require(ledger, term, "ledger")

print("SREV-038 schema/source gate passed")
