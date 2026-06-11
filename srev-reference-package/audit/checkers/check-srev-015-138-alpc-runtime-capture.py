#!/usr/bin/env python3
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-015/138 capture failed: {label} missing {needle!r}")


playbook = (ROOT / "docs/plan/srev-015-138-alpc-runtime-capture-playbook.md").read_text()
schema = json.loads(
    (ROOT / "docs/plan/srev-015-138-alpc-runtime-capture.schema.json").read_text()
)
srev015 = (ROOT / "docs/plan/srev-015-alpc-connect-flags.md").read_text()
srev138 = (ROOT / "docs/plan/srev-138-alpc-local-header-contract.md").read_text()
check015 = (ROOT / "docs/plan/check-srev-015.py").read_text()
check138 = (ROOT / "docs/plan/check-srev-138.py").read_text()

if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-015/138 capture failed: schema is not draft-07")
if schema.get("id") != "ALPC_RUNTIME_CAPTURE_EVIDENCE":
    raise SystemExit("SREV-015/138 capture failed: wrong schema id")

for term in [
    "official observation surface -> Windows runtime capture -> local ABI evidence -> source/schema decision",
    "local header names -> inferred Windows ABI truth -> behavior change",
    "SREV-138 must be interpreted before SREV-015",
    "If mirror-header proof fails, SREV-015 flag values are not legal evidence.",
    "NtAlpcConnectPort",
    "NtAlpcConnectPortEx",
    "NtAlpcSendWaitReceivePort",
    "SbieSvc AlpcRequestHandler",
    "driver endpoint policy",
    "ALPC_SYNC_CONNECTION",
    "PORT_INFO_CANIMPERSONATE",
    "ALPC_MESSAGE_FLAG_VIEW",
    "TotalLength < sizeof(PORT_MESSAGE)",
    "DataLength + sizeof(PORT_MESSAGE) > TotalLength",
]:
    require(playbook, term, "playbook")

for term in [
    "https://learn.microsoft.com/en-us/windows/win32/etw/alpc",
    "https://learn.microsoft.com/en-us/windows-hardware/drivers/debuggercmds/-lpc",
    "https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-security_quality_of_service",
]:
    require(playbook, term, "playbook official reference")

schema_text = json.dumps(schema, sort_keys=True)
for term in [
    "record_id",
    "windows_build",
    "architecture",
    "sandboxie_commit",
    "capture_tool",
    "endpoint_path",
    "source_path",
    "mirror_header",
    "port_message",
    "connect",
    "message_view",
    "negative_control",
    "evidence",
    "NtAlpcConnectPort",
    "NtAlpcConnectPortEx",
    "NtAlpcSendWaitReceivePort",
    "SbieSvc AlpcRequestHandler",
    "driver endpoint policy",
    "old LPC control",
    "drv_alpc_h",
    "common_win32_ntddk_h",
    "matches",
    "within_max_portmsg_length",
    "payload_bounds_valid",
    "post_wow64_mask_flags",
    "alpc_port_attributes_flags",
    "security_qos",
    "service_side_mask_result",
    "etw_trace",
    "debugger_transcript",
]:
    require(schema_text, term, "schema")

for term in [
    "Runtime Capture Matrix",
    "SREV-138 dependency",
    "ALPC_MESSAGE_VIEW sizeof and FIELD_OFFSET proof",
    "mirror-header proof matches capture build",
]:
    require(srev015, term, "SREV-015 adjacency")
    require(check015, term, "SREV-015 checker adjacency")

for term in [
    "Runtime Capture Matrix",
    "FIELD_OFFSET values",
    "mirror-header sizeof or FIELD_OFFSET drift",
]:
    require(srev138, term, "SREV-138 adjacency")
    require(check138, term, "SREV-138 checker adjacency")

print("SREV-015/138 ALPC runtime capture gate passed")
