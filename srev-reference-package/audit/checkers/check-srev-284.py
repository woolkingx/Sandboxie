#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-284 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-284 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-284-device-control-bootstrap-recursion-guard.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-284 failed: schema is not draft-07")
if schema.get("id") != "DEVICE_CONTROL_BOOTSTRAP_RECURSION_GUARD":
    raise SystemExit("SREV-284 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/dll/file_pipe.c":
    raise SystemExit("SREV-284 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "NtDeviceIoControlFile sends IOCTL codes",
    "IoControlCode selects the operation and buffer shape",
    "bootstrap guard before native pointer publication",
    "__sys_NtDeviceIoControlFile is the native pass-through owner",
    "SbieApi_Ioctl bypasses the hook",
    "STATUS_BAD_INITIAL_PC as a local sentinel",
    "SREV-281 owns the BlockNetParam TCP/NSI policy",
    "SREV-139 owns driver-side DeviceIoControl deny completion",
    "this SREV changes comments and proof only",
]:
    require(contracts, term, "schema")

file_pipe = (ROOT / "Sandboxie/core/dll/file_pipe.c").read_text()
sbieapi = (ROOT / "Sandboxie/core/dll/sbieapi.c").read_text()
spec = (ROOT / "docs/plan/srev-284-device-control-bootstrap-recursion-guard.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-284.md").read_text()
srev_281 = (ROOT / "docs/plan/ledger/srev-281.md").read_text()
srev_139 = (ROOT / "docs/plan/srev-139-deviceiocontrol-deny-iostatus.md").read_text()

start = file_pipe.index("_FX NTSTATUS File_NtDeviceIoControlFile(")
end = file_pipe.index("return status;", start)
func = file_pipe[start:end]

for term in [
    "SREV-284: during hook bootstrap __sys_NtDeviceIoControlFile",
    "can still be unpublished. Return the local sentinel so Sandboxie's",
    "monitor/API path does not re-enter the partially installed hook.",
    "if (!__sys_NtDeviceIoControlFile)",
    "return STATUS_BAD_INITIAL_PC;",
    "status = __sys_NtDeviceIoControlFile(",
    "FileHandle, Event, ApcRoutine, ApcContext, IoStatusBlock,",
    "IoControlCode, InputBuffer, InputBufferLength,",
    "OutputBuffer, OutputBufferLength);",
]:
    require(func, term, "File_NtDeviceIoControlFile source")

for stale in [
    "HACK HACK",
    "syscall instrumentation",
    "droppign",
    "dropping the one log entry",
]:
    reject(func, stale, "File_NtDeviceIoControlFile stale comment")

sbie_start = sbieapi.index("if (status != STATUS_SUCCESS) {")
sbie_end = sbieapi.index("return status;", sbie_start)
sbie_block = sbieapi[sbie_start:sbie_end]
for term in [
    "} else*/ if (__sys_NtDeviceIoControlFile) {",
    "once NtDeviceIoControlFile is hooked, bypass it",
    "status = __sys_NtDeviceIoControlFile(",
    "} else {",
    "status = NtDeviceIoControlFile(",
]:
    require(sbie_block, term, "SbieApi_Ioctl adjacency")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "DEVICE_CONTROL_BOOTSTRAP_RECURSION_GUARD",
    "srev-284-device-control-bootstrap-recursion-guard.schema.json",
    "SbieApi_Ioctl",
    "STATUS_BAD_INITIAL_PC",
    "SREV-281",
    "SREV-139",
]:
    require(spec, term, "spec")

for term in [
    "NET_PARAM_DEVICE_CONTROL_COMPARTMENT_BOUNDARY",
    "TCP/NSI",
    "File_NtDeviceIoControlFile",
]:
    require(srev_281, term, "SREV-281 adjacency")

for term in [
    "DEVICEIOCONTROL_DENY_IOSTATUS_COMPLETION",
    "file_ctrl.c",
    "syscall-level",
    "IO_STATUS_BLOCK",
]:
    require(srev_139, term, "SREV-139 adjacency")

for term in [
    "### SREV-284: Device-Control Bootstrap Recursion Guard",
    "DEVICE_CONTROL_BOOTSTRAP_RECURSION_GUARD",
    "srev-284-device-control-bootstrap-recursion-guard.schema.json",
    "Sandboxie/core/dll/file_pipe.c",
    "SbieApi_Ioctl",
    "STATUS_BAD_INITIAL_PC",
    "SREV-281",
    "SREV-139",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-284 source gate passed")
