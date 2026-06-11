#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-006B failed: {label} missing {needle!r}")


def assert_before(text: str, label: str, earlier: str, later: str) -> None:
    e = text.find(earlier)
    l = text.find(later)
    if e < 0 or l < 0 or e > l:
        raise SystemExit(f"SREV-006B failed: {label}")


schema = json.loads((ROOT / "docs/plan/srev-006b-service-name-spec.schema.json").read_text())
if schema.get("id") != "SERVICE_BROKER_NAME_SHAPE":
    raise SystemExit("SREV-006B failed: schema missing SERVICE_BROKER_NAME_SHAPE")

contracts = "\n".join(schema["contracts"])
for term in [
    "OpenServiceW lpServiceName maximum length is 256 characters",
    "Service-name gate must reject name_len > 256",
    "Service-name gate must require name[name_len] == L'\\0'",
]:
    require(contracts, term, "schema contracts")

src = (ROOT / "Sandboxie/core/svc/serviceserver.cpp").read_text()
spec = (ROOT / "docs/plan/srev-006b-service-name-spec.md").read_text()
ledger = read_combined_ledger(ROOT)

for term in [
    "Service_CheckName",
    "name_len > 256",
    "available < sizeof(WCHAR)",
    "name_len > (available / sizeof(WCHAR)) - 1",
    "name[name_len] != L'\\0'",
    "Service_CheckName(req->h.length, offset, req->name_len, req->name)",
]:
    require(src, term, "service source")

assert_before(src, "start service gate before OpenService",
              "Service_CheckName(req->h.length, offset, req->name_len, req->name)",
              "OpenService(handle1, req->name, SERVICE_START)")

query_handler = src.find("MSG_HEADER *ServiceServer::QueryHandler")
second_gate = src.find("Service_CheckName(req->h.length, offset, req->name_len, req->name)", query_handler)
query_open = src.find("OpenService(\n        handle1, req->name, SERVICE_QUERY_STATUS")
if second_gate < 0 or query_open < 0 or second_gate > query_open:
    raise SystemExit("SREV-006B failed: query service gate must precede OpenService")

for term in ["OpenServiceW", "string length of 256 characters", "name[name_len] == L'\\0'"]:
    require(spec, term, "spec")

require(ledger, "### SREV-006: Broker Request Fixed Strings Are Used Before NUL-Terminator Proof", "ledger")
require(ledger, "Sandboxie/core/svc/serviceserver.cpp", "ledger")

print("SREV-006B schema/source gate passed")
