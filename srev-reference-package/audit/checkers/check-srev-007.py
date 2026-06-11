#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-007 failed: {label} missing {needle!r}")


schema = json.loads((ROOT / "docs/plan/srev-007-service-start-policy-spec.schema.json").read_text())
if schema.get("id") != "SERVICE_START_POLICY_POSTURE":
    raise SystemExit("SREV-007 failed: schema missing SERVICE_START_POLICY_POSTURE")
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-007 failed: schema is not draft-07")

src = (ROOT / "Sandboxie/core/svc/serviceserver.cpp").read_text()
spec = (ROOT / "docs/plan/srev-007-service-start-policy-spec.md").read_text()
ledger = read_combined_ledger(ROOT)

impersonate = src.find("PipeServer::ImpersonateCaller(&msg)")
start_dispatch = src.find("msg->msgid == MSGID_SERVICE_START")
open_service = src.find("OpenService(handle1, req->name, SERVICE_START)")
name_gate = src.find("Service_CheckName(req->h.length, offset, req->name_len, req->name)")
if min(impersonate, start_dispatch, open_service, name_gate) < 0:
    raise SystemExit("SREV-007 failed: missing service-start topology marker")
if not (impersonate < start_dispatch < name_gate < open_service):
    raise SystemExit("SREV-007 failed: impersonation/name-gate/SCM order changed")

for term in [
    "OpenServiceW",
    "StartServiceW",
    "SCM/service DACL checks",
    "the host service object's SCM DACL is the current",
    "authorization owner for `SERVICE_START`",
    "not a silent replacement of SCM DACL semantics",
]:
    require(spec, term, "spec")

for term in [
    "SREV-007: Handler impersonates the caller before dispatch",
    "delegates authorization to the",
    "service object's SCM DACL through OpenService(..., SERVICE_START)",
    "Do not add an admin-only or elevation-style gate here",
    "explicit allowlist",
]:
    require(src, term, "source policy comment")

for stale in [
    "should do:",
    "if (! IsAdmin())",
    "CanCallerDoElevation",
]:
    if stale in src:
        raise SystemExit(f"SREV-007 failed: stale policy comment remains {stale!r}")

require(ledger, "### SREV-007: Service Start Broker Relies On SCM ACL Instead Of Sandboxie Policy Gate", "ledger")
require(ledger, "Sandboxie/core/svc/serviceserver.cpp", "ledger")
require(ledger, "patched comment/policy classification after official SCM access review", "ledger")

print("SREV-007 schema/source gate passed")
