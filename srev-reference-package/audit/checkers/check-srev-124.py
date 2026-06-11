#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-124 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-124 failed: {label} still contains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-124-sbieapi-ioctl-close-request-boundary.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-124 failed: schema is not draft-07")
if schema.get("id") != "SBIEAPI_IOCTL_CLOSE_REQUEST_BOUNDARY":
    raise SystemExit("SREV-124 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "SbieApi_Ioctl NULL parms is a close request used by kmdutil",
    "null close request closes cached SbieApi_DeviceHandle when it exists",
    "null close request invalidates SbieApi_DeviceHandle",
    "null close request returns before trace open or device ioctl logic can read parms zero or reopen the driver device",
    "null close request reports NtClose status when a handle existed otherwise STATUS_SUCCESS",
    "non-null request preserves trace driver-open STATUS_SERVER_DISABLED remap hook-bypass and ioctl topology",
]:
    require(contracts, term, "schema")

source = (ROOT / "Sandboxie/core/dll/sbieapi.c").read_text()
spec = (ROOT / "docs/plan/srev-124-sbieapi-ioctl-close-request-boundary.md").read_text()
ledger = read_combined_ledger(ROOT)

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

ioctl = source[
    source.index("_FX NTSTATUS SbieApi_Ioctl"):
    source.index("// SbieApi_CallFunc")
]

close_block = """if (parms == NULL) { // close request as used by kmdutil
        status = STATUS_SUCCESS;
        if(SbieApi_DeviceHandle != INVALID_HANDLE_VALUE)
            status = NtClose(SbieApi_DeviceHandle);
        SbieApi_DeviceHandle = INVALID_HANDLE_VALUE;
        return status;
    }"""
require(ioctl, close_block, "SbieApi_Ioctl close request")

if ioctl.index("return status;") > ioctl.index("if (Dll_SbieTrace && parms[0] != API_MONITOR_PUT2)"):
    raise SystemExit("SREV-124 failed: close request return is after trace/parms[0] path")

reject(ioctl, """if (parms == NULL) { // close request as used by kmdutil
        if(SbieApi_DeviceHandle != INVALID_HANDLE_VALUE)
            NtClose(SbieApi_DeviceHandle);
        SbieApi_DeviceHandle = INVALID_HANDLE_VALUE;
    }

    if (Dll_SbieTrace && parms[0] != API_MONITOR_PUT2)""", "fallthrough close request")

for term in [
    "if (Dll_SbieTrace && parms[0] != API_MONITOR_PUT2)",
    "RtlInitUnicodeString(&uni, API_DEVICE_NAME);",
    "NtOpenFile(",
    "status = STATUS_SERVER_DISABLED;",
    "__sys_NtDeviceIoControlFile",
    "NtDeviceIoControlFile(",
    "API_SBIEDRV_CTLCODE",
    "parms, sizeof(ULONG64) * 8, NULL, 0",
]:
    require(ioctl, term, "normal ioctl path")

for term in [
    "### SREV-124: SbieApi Ioctl Close Request Boundary",
    "SBIEAPI_IOCTL_CLOSE_REQUEST_BOUNDARY",
    "srev-124-sbieapi-ioctl-close-request-boundary.schema.json",
    "Sandboxie/core/dll/sbieapi.c",
    "SbieApi_Ioctl",
    "SbieApi_DeviceHandle",
    "NtClose",
    "NtOpenFile",
    "NtDeviceIoControlFile",
    "API_SBIEDRV_CTLCODE",
]:
    require(ledger, term, "ledger")

print("SREV-124 schema/source gate passed")
