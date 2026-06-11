#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-281 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-281 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-281-net-param-device-control-compartment-boundary.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-281 failed: schema is not draft-07")
if schema.get("id") != "NET_PARAM_DEVICE_CONTROL_COMPARTMENT_BOUNDARY":
    raise SystemExit("SREV-281 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/dll/file_init.c":
    raise SystemExit("SREV-281 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "NtDeviceIoControlFile hook registration for BlockNetParam",
    "IOCTL codes to a device driver",
    "IoControlCode determines the operation and buffer shape",
    "private IOCTLs can be device-specific",
    "only for non-compartment boxes",
    "TCP and NSI network-parameter IOCTL deny logic",
    "native device-control route for ICMP/IP helper behavior",
    "IpHlp_Init skips ICMP helper hooks in compartment mode",
    "this SREV changes comments and proof only",
]:
    require(contracts, term, "schema")

file_init = (ROOT / "Sandboxie/core/dll/file_init.c").read_text()
file_pipe = (ROOT / "Sandboxie/core/dll/file_pipe.c").read_text()
iphlp = (ROOT / "Sandboxie/core/dll/iphlp.c").read_text()
dllmain = (ROOT / "Sandboxie/core/dll/dllmain.c").read_text()
settings = (ROOT / "Sandboxie/install/SbieSettings.ini").read_text()
spec = (ROOT / "docs/plan/srev-281-net-param-device-control-compartment-boundary.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-281.md").read_text()

init_start = file_init.index("SBIEDLL_HOOK(File_,NtFsControlFile);")
init_end = file_init.index("RtlGetFullPathName_UEx", init_start)
init_block = file_init[init_start:init_end]

for term in [
    "SREV-281: compartment mode keeps the native device-control route",
    "for ICMP/IP helper behavior.  The BlockNetParam TCP/NSI IOCTL",
    "deny hook belongs to non-compartment boxes.",
    "if (!Dll_CompartmentMode)",
    "if (File_IsBlockedNetParam(NULL))",
    "SBIEDLL_HOOK(File_,NtDeviceIoControlFile);",
]:
    require(init_block, term, "file_init hook registration block")

reject(init_block, "else ping does not work", "file_init stale comment")

for term in [
    "return SbieApi_QueryConfBool(BoxName, L\"BlockNetParam\", TRUE);",
]:
    require(file_init, term, "File_IsBlockedNetParam")

for term in [
    "Dll_CompartmentMode = SbieApi_QueryConfBool(NULL, L\"SetCompartmentMode\", (Dll_ProcessFlags & SBIE_FLAG_APP_COMPARTMENT) != 0);",
]:
    require(dllmain, term, "Dll_CompartmentMode setup")

pipe_start = file_pipe.index("_FX NTSTATUS File_NtDeviceIoControlFile(")
pipe_end = file_pipe.index("status = __sys_NtDeviceIoControlFile", pipe_start)
pipe_block = file_pipe[pipe_start:pipe_end]
for term in [
    "IoControlCode == 0x00128004",
    "IoControlCode == 0x00120013",
    "_wcsicmp(TruePath + 8, L\"TCP\") == 0",
    "_wcsicmp(TruePath + 8, L\"NSI\") == 0",
    "DenyAccess = TRUE;",
    "SbieApi_Log(1314, Dll_ImageName);",
    "return STATUS_ACCESS_DENIED;",
]:
    require(pipe_block, term, "File_NtDeviceIoControlFile deny block")

for term in [
    "if (Dll_CompartmentMode || Dll_OsBuild < 6000) { // in compartment mode we have a full token so no need to hook anything here",
    "SBIEDLL_HOOK(IpHlp_,IcmpCreateFile);",
    "SBIEDLL_HOOK(IpHlp_,IcmpSendEcho);",
    "SBIEDLL_HOOK(IpHlp_,IcmpSendEcho2);",
]:
    require(iphlp, term, "IpHlp_Init adjacency")

for term in [
    "[BlockNetParam]",
    "Syntax=[sn]=[bY]",
    "Description=Blocks access to certain network parameters.",
    "[SetCompartmentMode]",
    "SBIE_FLAG_APP_COMPARTMENT",
]:
    require(settings, term, "SbieSettings local config")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "NET_PARAM_DEVICE_CONTROL_COMPARTMENT_BOUNDARY",
    "srev-281-net-param-device-control-compartment-boundary.schema.json",
    "File_NtDeviceIoControlFile",
    "IpHlp_Init",
    "BlockNetParam",
    "TCP/NSI",
]:
    require(spec, term, "spec")

for term in [
    "### SREV-281: Net Param Device-Control Compartment Boundary",
    "NET_PARAM_DEVICE_CONTROL_COMPARTMENT_BOUNDARY",
    "srev-281-net-param-device-control-compartment-boundary.schema.json",
    "Sandboxie/core/dll/file_init.c",
    "BlockNetParam",
    "NtDeviceIoControlFile",
    "IcmpSendEcho",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-281 source gate passed")
