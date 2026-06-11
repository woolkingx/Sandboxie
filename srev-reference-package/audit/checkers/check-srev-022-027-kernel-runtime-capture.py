#!/usr/bin/env python3
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-022/027 capture failed: {label} missing {needle!r}")


playbook = (ROOT / "docs/plan/srev-022-027-kernel-runtime-capture-playbook.md").read_text()
schema = json.loads(
    (ROOT / "docs/plan/srev-022-027-kernel-runtime-capture.schema.json").read_text()
)
srev022 = (ROOT / "docs/plan/srev-022-font-token-subject-context.md").read_text()
srev027 = (ROOT / "docs/plan/srev-027-wfp-classify-logging-irql.md").read_text()
check022 = (ROOT / "docs/plan/check-srev-022.py").read_text()
check027 = (ROOT / "docs/plan/check-srev-027.py").read_text()

if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-022/027 capture failed: schema is not draft-07")
if schema.get("id") != "KERNEL_RUNTIME_CAPTURE_EVIDENCE":
    raise SystemExit("SREV-022/027 capture failed: wrong schema id")

for term in [
    "official kernel DDI shape -> Windows runtime capture -> local owner decision",
    "local compatibility path works once -> kernel ownership and IRQL contracts are satisfied",
    "feature path: `font-token-subject-context`",
    "feature path: `wfp-deferred-logger`",
    "unsupported SECURITY_SUBJECT_CONTEXT token substitution",
    "PASSIVE_LEVEL executor",
    "Digital Guardian or equivalent endpoint",
    "Inline logging negative control",
]:
    require(playbook, term, "playbook")

for term in [
    "https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/ns-wdm-_access_state",
    "https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/ns-wdm-_security_subject_context",
    "https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/fwpsk/nc-fwpsk-fwps_callout_classify_fn0",
    "https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-exallocatepool2",
]:
    require(playbook, term, "playbook official reference")

schema_text = json.dumps(schema, sort_keys=True)
for term in [
    "record_id",
    "windows_build",
    "architecture",
    "sandboxie_commit",
    "driver_build",
    "feature_path",
    "font-token-subject-context",
    "wfp-deferred-logger",
    "route_result",
    "font-token-substituted",
    "wfp-deferred-written",
    "negative-control-passed",
    "verifier-failure",
    "path_topology",
    "minifilter-irp-mj-create",
    "xp-parse-proc",
    "kernel-win32k-delayed-font-open",
    "real-fonts-path",
    "sandbox-boxed-font-path",
    "exact-font-read-execute",
    "subject_context_before",
    "subject_context_after",
    "reference_delta",
    "downstream_release_observed",
    "restore_observed",
    "digital_guardian_regression",
    "irql",
    "DISPATCH_LEVEL",
    "capture_allocation",
    "pool_tag",
    "allocation_failure_policy",
    "producer_synchronization",
    "passive_worker_observed",
    "session_monitor_call_irql",
    "inline_negative_control",
    "no_session_monitor_put",
    "no_rtl_stringcb_printf",
    "no_eresource",
    "no_pageable_buffer",
    "no_session_monitor_log_touch",
    "monitor_log_readback",
]:
    require(schema_text, term, "schema")

for term in [
    "Shared Runtime Capture Evidence",
    "srev-022-027-kernel-runtime-capture.schema.json",
    "srev-022-027-kernel-runtime-capture-playbook.md",
    "font-token-subject-context",
    "Windows gate: validate captured font-token records",
]:
    require(srev022, term, "SREV-022 adjacency")
    require(check022, term, "SREV-022 checker adjacency")

for term in [
    "Shared Runtime Capture Evidence",
    "srev-022-027-kernel-runtime-capture.schema.json",
    "srev-022-027-kernel-runtime-capture-playbook.md",
    "wfp-deferred-logger",
    "Windows gate: validate captured WFP logger records",
]:
    require(srev027, term, "SREV-027 adjacency")
    require(check027, term, "SREV-027 checker adjacency")

print("SREV-022/027 kernel runtime capture gate passed")
