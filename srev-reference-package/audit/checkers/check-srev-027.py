#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-027 failed: {label} missing {needle!r}")


schema = json.loads((ROOT / "docs/plan/srev-027-wfp-classify-logging-irql.schema.json").read_text())
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-027 failed: schema is not draft-07")
if schema.get("id") != "WFP_CLASSIFY_LOGGING_IRQL_CONTRACT":
    raise SystemExit("SREV-027 failed: schema missing WFP_CLASSIFY_LOGGING_IRQL_CONTRACT")

contracts = "\n".join(schema["contracts"])
for term in [
    "Runtime matrix must require Driver Verifier IRQL/DDI checking",
    "negative controls",
    "logging-disabled regression",
    "Deferred logger design must separate DISPATCH_LEVEL nonpaged classify-side capture",
    "shared kernel runtime capture records must use feature_path wfp-deferred-logger",
]:
    require(contracts, term, "schema")

matrix = "\n".join(
    "\n".join(value) if isinstance(value, list) else str(value)
    for value in schema["runtime_capture_matrix"].values()
)
for term in [
    "Driver Verifier IRQL checking",
    "DDI compliance checking",
    "Special Pool for logger tag",
    "forced allocation failure",
    "IPv4 TCP outbound",
    "IPv6 UDP outbound",
    "loopback traffic",
    "blocked traffic",
    "permitted traffic",
    "NetFwTrace enabled",
    "NetFwTrace disabled",
    "rule refresh while traffic is active",
    "process id",
    "remote address",
    "remote port",
    "NetFwTrace enabled bit",
    "nonpaged fixed-size record",
    "bounded queue or ring capacity",
    "overflow or drop counter",
    "DISPATCH-safe producer lock or lock-free queue",
    "no ERESOURCE in WFP_classify",
    "no pageable buffer in WFP_classify",
    "PASSIVE_LEVEL worker",
    "calls Session_MonitorPut or Session_MonitorPutEx outside classify",
    "drains or cancels on WFP unload",
    "drop or overflow diagnostic",
    "no direct Session_MonitorPut from WFP_classify",
    "no direct RtlStringCbPrintfW from WFP_classify",
    "logging disabled path preserves block permit decisions",
]:
    require(matrix, term, "schema runtime capture matrix")

src = (ROOT / "Sandboxie/core/drv/wfp.c").read_text()
spec = (ROOT / "docs/plan/srev-027-wfp-classify-logging-irql.md").read_text()
ledger = read_combined_ledger(ROOT)

start = src.index("// WFP_classify")
start = src.index("void WFP_classify(", start)
end = src.index("//---------------------------------------------------------------------------\n// WFP_notify", start)
body = src[start:end]

for forbidden in [
    "Session_MonitorPut(",
    "Session_MonitorPutEx(",
    "RtlStringCbPrintfA(",
    "RtlStringCbPrintfW(",
]:
    if forbidden in body:
        raise SystemExit(f"SREV-027 failed: unsafe inline logging residue remains: {forbidden!r}")

for required in [
    "BOOLEAN log = FALSE;",
    "log = wfp_proc->LogTraffic;",
    "WFP_TraceEnqueueFromClassify(processId, send, v6, &remote_ip, remote_port, (UCHAR)protocol, block);",
]:
    if required not in body:
        raise SystemExit(f"SREV-027 failed: classify deferred trace path missing {required!r}")

for required in [
    "typedef struct _WFP_TRACE_RECORD",
    "WFP_TRACE_QUEUE_CAPACITY 256",
    "static WFP_TRACE_RECORD* WFP_TraceQueue",
    "static ULONG WFP_TraceDropCount",
    "static KSPIN_LOCK WFP_TraceLock",
    "static KEVENT WFP_TraceEvent",
    "static HANDLE WFP_TraceThreadHandle",
    "BOOLEAN WFP_TraceStart(void)",
    "void WFP_TraceStop(void)",
    "void WFP_TraceEnqueueFromClassify(",
    "void WFP_TraceThreadProc(PVOID StartContext)",
    "void WFP_TraceWrite(const WFP_TRACE_RECORD* record)",
    "PsCreateSystemThread(",
    "KeWaitForSingleObject(&WFP_TraceEvent, Executive, KernelMode, FALSE, NULL);",
    "WFP_TraceQueueCount == WFP_TRACE_QUEUE_CAPACITY",
    "++WFP_TraceDropCount;",
    "WFP_TraceStart()",
    "WFP_TraceStop();",
    "Session_MonitorPut(",
    "RtlStringCbPrintfW(",
]:
    require(src, required, "source deferred logger")

for term in [
    "https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/fwpsk/nc-fwpsk-fwps_callout_classify_fn0",
    "https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntstrsafe/nf-ntstrsafe-rtlstringcbprintfa",
    "https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-keinitializeevent",
    "https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-kesetevent",
    "https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-kewaitforsingleobject",
    "https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-pscreatesystemthread",
    "https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/nf-ntifs-zwwaitforsingleobject",
    "https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-exacquireresourceexclusivelite",
    "https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-exallocatepool2",
    "event storage to be resident",
    "Wait = FALSE",
    "Timeout = NULL",
    "PASSIVE_LEVEL",
    "PsTerminateSystemThread",
    "deferred logger",
    "executable deferred logger",
    "Runtime Verification Matrix",
    "Deferred Logger Matrix",
    "Shared Runtime Capture Evidence",
    "srev-022-027-kernel-runtime-capture-playbook.md",
    "srev-022-027-kernel-runtime-capture.schema.json",
    "wfp-deferred-logger",
    "Windows gate: validate captured WFP logger records",
    "Driver Verifier with IRQL checking / DDI compliance",
    "sustained outbound TCP",
    "IPv6",
    "`NetFwTrace=y`",
    "PASSIVE_LEVEL",
    "allocation-failure policy",
    "no pageable function in",
    "no verifier violation",
    "logging is disabled",
]:
    require(spec, term, "spec")

for term in [
    "### SREV-027: WFP Classify NetFwTrace Deferred Logger Path",
    "DISPATCH_LEVEL",
    "Session_MonitorPut",
    "deferred logger",
    "executable deferred logger",
    "Deferred Logger Matrix",
    "PASSIVE-level monitor formatting",
    "Driver Verifier IRQL checking",
]:
    require(ledger, term, "ledger")

print("SREV-027 schema/source gate passed")
