#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-015 failed: {label} missing {needle!r}")


def reject_any(files: dict, needle: str) -> None:
    for label, text in files.items():
        if needle in text:
            raise SystemExit(f"SREV-015 failed: {label} still contains naked constant {needle!r}")


schema = json.loads((ROOT / "docs/plan/srev-015-alpc-connect-flags.schema.json").read_text())
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-015 failed: schema is not draft-07")
if schema.get("id") != "ALPC_CONNECT_FLAGS_POSTURE":
    raise SystemExit("SREV-015 failed: schema missing ALPC_CONNECT_FLAGS_POSTURE")

contracts = "\n".join(schema["contracts"])
for term in [
    "Source comments name SREV-015",
    "Do not invent new flag bits without Windows runtime capture",
    "SREV-138 mirror-header proof",
    "SREV-015 and SREV-138 share docs/plan/srev-015-138-alpc-runtime-capture.schema.json",
]:
    require(contracts, term, "schema")

matrix = "\n".join(
    "\n".join(value) if isinstance(value, list) else str(value)
    for value in schema["runtime_capture_matrix"].values()
)
for term in [
    "supported Windows 10 x86",
    "supported Windows 10 x64",
    "supported Windows 11 x64",
    "supported Windows 11 ARM64 where built",
    "\\RPC Control\\ntsvcs",
    "\\RPC Control\\plugplay",
    "non-proxied ALPC endpoint negative control",
    "old-LPC max_msg_len == -1 control",
    "NtAlpcConnectPort",
    "NtAlpcConnectPortEx",
    "NtAlpcSendWaitReceivePort",
    "SbieSvc AlpcRequestHandler",
    "driver endpoint policy observation",
    "connection flags before PORT_INFO_WOW64_PROCESS masking",
    "connection flags after PORT_INFO_WOW64_PROCESS masking",
    "ALPC_PORT_ATTRIBUTES.Flags",
    "SecurityQos",
    "MaxMessageLength",
    "process architecture",
    "SendFlags",
    "ReceiveFlags",
    "ViewAttrs",
    "unmap special case",
    "service-side view mask result",
    "ALPC ETW class enabled",
    "debugger !alpc readback",
    "ALPC_MESSAGE_VIEW sizeof and FIELD_OFFSET proof",
    "mirror-header proof matches capture build",
    "unknown ALPC_MESSAGE_VIEW bits outside accepted mask",
    "non-ntsvcs non-plugplay endpoint preserves native behavior",
]:
    require(matrix, term, "schema runtime capture matrix")

ipc = (ROOT / "Sandboxie/core/dll/ipc.c").read_text()
svc = (ROOT / "Sandboxie/core/svc/namedpipeserver.cpp").read_text()
spec = (ROOT / "docs/plan/srev-015-alpc-connect-flags.md").read_text()
shared_playbook = (ROOT / "docs/plan/srev-015-138-alpc-runtime-capture-playbook.md").read_text()
shared_schema = json.loads((ROOT / "docs/plan/srev-015-138-alpc-runtime-capture.schema.json").read_text())
ledger = read_combined_ledger(ROOT)

if shared_schema.get("id") != "ALPC_RUNTIME_CAPTURE_EVIDENCE":
    raise SystemExit("SREV-015 failed: shared ALPC capture schema has wrong id")
require(shared_playbook, "SREV-138 must be interpreted before SREV-015", "shared capture playbook")

for term in [
    "PORT_INFO_WOW64_PROCESS",
    "ALPC_SYNC_CONNECTION",
    "PORT_INFO_CANIMPERSONATE",
    "ALPC_MESSAGE_FLAG_VIEW",
    "SREV-015: if ALPC, accept only the locally named connection shape",
    "Microsoft does not publish",
    "Windows ALPC ETW/debugger capture and the SREV-138 mirror",
    "requires Windows capture and SREV-138 mirror-header proof rather than",
    "SREV-015: ALPC message-view flags are private/local-observed shapes.",
]:
    require(ipc, term, "DLL ipc source")

for term in [
    "PORT_INFO_CANIMPERSONATE",
    "ALPC_SYNC_CONNECTION",
    "ALPC_MESSAGE_FLAG_VIEW",
    "SREV-015: keep the locally observed ALPC view flag mask.",
    "Windows capture and SREV-138 mirror-header proof rather than",
]:
    require(svc, term, "service source")

for naked in [
    "AlpcConnectionFlags != 0x20000",
    "alpc_info->Flags != 0x10000",
    "alpc.Flags = 0x10000",
    "if alpc, make sure specific (yet unknown) parameters are given",
    "we only accept 0x20000000 or 0x40000000 or 0x60000000",
]:
    reject_any({"DLL ipc": ipc, "service": svc}, naked)

for term in [
    "AlpcConnectRequest",
    "AlpcConnectSuccess",
    "AlpcConnectFail",
    "connection flags",
    "ALPC_PORT_ATTRIBUTES.Flags",
    "message view SendFlags/ReceiveFlags",
    "source paths: NtAlpcConnectPort, NtAlpcConnectPortEx, NtAlpcSendWaitReceivePort",
    "Runtime Capture Matrix",
    "SREV-138 dependency",
    "docs/plan/srev-015-138-alpc-runtime-capture-playbook.md",
    "docs/plan/srev-015-138-alpc-runtime-capture.schema.json",
    "non-proxied ALPC endpoint negative control",
    "runtime capture",
]:
    require(spec, term, "spec")

require(ledger, "### SREV-015: ALPC Connect Proxy Uses Unknown Magic Flags", "ledger")
require(ledger, "Sandboxie/core/dll/ipc.c", "ledger")
require(ledger, "patched source-level ALPC official observation map", "ledger")
require(ledger, "needs Windows runtime proof", "ledger")
require(ledger, "Runtime Capture Matrix", "ledger")
require(ledger, "SREV-138 mirror-header proof", "ledger")

print("SREV-015 schema/source gate passed")
