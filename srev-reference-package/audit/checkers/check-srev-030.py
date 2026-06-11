#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-030 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-030 failed: {label} still contains {needle!r}")


api = json.loads((ROOT / "docs/plan/srev-030-service-query.schema.json").read_text())
if api.get("id") != "SERVICE_QUERY":
    raise SystemExit("SREV-030 failed: schema missing SERVICE_QUERY")

if "request" in api:
    segment = api["request"]["segments"][0]
    if segment.get("max_chars") != 256 or not segment.get("nul_terminated"):
        raise SystemExit("SREV-030 failed: SERVICE_QUERY schema name shape is wrong")
else:
    audit_contract = api["properties"]["audit_contract"]["description"]
    for term in [
        "request:",
        "\"payload_offset\": \"FIELD_OFFSET(SERVICE_QUERY_REQ, name)\"",
        "\"segments\": [",
        "\"max_chars\": 256",
        "\"nul_terminated\": true",
    ]:
        require(audit_contract, term, "SERVICE_QUERY audit contract")

src = (ROOT / "Sandboxie/core/dll/scm_query.c").read_text()
spec = (ROOT / "docs/plan/srev-030-service-query-sender-name.md").read_text()
ledger = read_combined_ledger(ROOT)

for term in [
    "#define SCM_SERVICE_NAME_MAX_CHARS 256",
    "if (! ServiceNm)",
    "name_len_size = wcslen(ServiceNm);",
    "name_len_size > SCM_SERVICE_NAME_MAX_CHARS",
    "req_len = sizeof(SERVICE_QUERY_REQ)",
    "if (req_len > sizeof(u))",
    "memcpy(u.req.name, ServiceNm, (name_len + 1) * sizeof(WCHAR));",
    "u.req.h.length = req_len;",
]:
    require(src, term, "source")

reject(src, "wcscpy(u.req.name, ServiceNm)", "source")

boxed = src.index("Scm_IsBoxedService(ServiceNm)")
limit = src.index("name_len_size = wcslen(ServiceNm);")
if boxed > limit:
    raise SystemExit("SREV-030 failed: boxed-service path should stay before real-service max gate")

for term in [
    "https://learn.microsoft.com/en-us/windows/win32/api/winsvc/nf-winsvc-openservicew",
    "srev-030-service-query.schema.json",
    "256 characters",
]:
    require(spec, term, "spec")

for term in [
    "### SREV-030: Service Query Sender Name Shape",
    "SCM_SERVICE_NAME_MAX_CHARS",
    "SERVICE_QUERY",
    "wcscpy(u.req.name, ServiceNm)",
]:
    require(ledger, term, "ledger")

print("SREV-030 schema/source gate passed")
