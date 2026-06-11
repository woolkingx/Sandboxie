#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-139 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-139 failed: {label} still contains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-139-deviceiocontrol-deny-iostatus.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-139 failed: schema is not draft-07")
if schema.get("id") != "DEVICEIOCONTROL_DENY_IOSTATUS_COMPLETION":
    raise SystemExit("SREV-139 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "file_ctrl.c owns syscall-level filtering before native NtDeviceIoControlFile sees blocked mount manager or CMApi IOCTLs",
    "IOCTL routing is based on the official CTL_CODE bit layout plus local function denylist policy",
    "CMApi function numbers remain a local policy projection because Microsoft does not publish the DeviceApi CMApi wire protocol",
    "When Sandboxie fabricates a final deny for NtDeviceIoControlFile it must also become the completion owner for the caller IO_STATUS_BLOCK",
    "A fabricated deny writes Status = STATUS_ACCESS_DENIED and Information = 0 before returning STATUS_ACCESS_DENIED",
    "The fabricated completion write is guarded by ProbeForWrite and remains inside the outer syscall exception boundary",
    "Allowed IOCTLs still flow to native NtDeviceIoControlFile unchanged",
]:
    require(contracts, term, "schema")

source = (ROOT / "Sandboxie/core/drv/file_ctrl.c").read_text()
syscall = (ROOT / "Sandboxie/core/drv/syscall.c").read_text()
syscall_open = (ROOT / "Sandboxie/core/drv/syscall_open.c").read_text()
process_h = (ROOT / "Sandboxie/core/drv/process.h").read_text()
file_c = (ROOT / "Sandboxie/core/drv/file.c").read_text()
settings = (ROOT / "Sandboxie/install/SbieSettings.ini").read_text()
setup = (ROOT / "Sandboxie/core/dll/setup.c").read_text()
api_defs = (ROOT / "Sandboxie/core/drv/api_defs.h").read_text()
spec = (ROOT / "docs/plan/srev-139-deviceiocontrol-deny-iostatus.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-139.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "Syscall_Set1(\"DeviceIoControlFile\", Syscall_DeviceIoControlFile)",
    "__try {",
    "status = entry->handler1_func(proc, entry, user_args);",
    "} __except (EXCEPTION_EXECUTE_HANDLER) {",
    "status = GetExceptionCode();",
]:
    require(syscall, term, "syscall outer boundary")

for term in [
    "#include \"file_ctrl.c\"",
]:
    require(syscall_open, term, "syscall_open include boundary")

for term in [
    "BOOLEAN file_open_devapi_cmapi;",
]:
    require(process_h, term, "process config field")

for term in [
    "proc->file_open_devapi_cmapi = Conf_Get_Boolean(proc->box->name, L\"OpenDevCMApi\", 0, FALSE);",
]:
    require(file_c, term, "file init config")

for term in [
    "[OpenDevCMApi]",
    "Controls whether sandboxed processes can open Device Configuration Manager API (CMApi) device objects.",
]:
    require(settings, term, "settings surface")

for term in [
    "most of the CM_ functions use the \"\\Device\\DeviceApi\\CMApi\" device/file for communication",
    "these requests are filtered by the driver and we let them silently fail",
]:
    require(setup, term, "CMApi local comment")

for term in [
    "#define CTL_CODE( DeviceType, Function, Method, Access )",
    "((DeviceType) << 16) | ((Access) << 14) | ((Function) << 2) | (Method)",
]:
    require(api_defs, term, "local CTL_CODE")

for term in [
    "#define DEVICE_TYPE_FROM_CTL_CODE(ctrlCode)",
    "#define FUNCTION_FROM_CTL_CODE(ctrlCode)",
    "#define METHOD_FROM_CTL_CODE(ctrlCode)",
    "static NTSTATUS File_DenyDeviceIoControlFile(PIO_STATUS_BLOCK IoStatusBlock)",
    "ProbeForWrite(IoStatusBlock, sizeof(IO_STATUS_BLOCK), sizeof(ULONG_PTR));",
    "IoStatusBlock->Status = STATUS_ACCESS_DENIED;",
    "IoStatusBlock->Information = 0;",
    "return STATUS_ACCESS_DENIED;",
    "DEVICE_TYPE_FROM_CTL_CODE(IoControlCode) == 0x6d",
    "IOCTL_MOUNTMGR_CREATE_POINT",
    "IOCTL_MOUNTMGR_DELETE_POINTS (DeleteVolumeMountPoint())",
    "IOCTL_MOUNTMGR_DELETE_POINTS_DBONLY",
    "IOCTL_MOUNTMGR_VOLUME_MOUNT_POINT_CREATED",
    "IOCTL_MOUNTMGR_VOLUME_MOUNT_POINT_DELETED",
    "IOCTL_MOUNTMGR_KEEP_LINKS_WHEN_OFFLINE",
    "return File_DenyDeviceIoControlFile((PIO_STATUS_BLOCK)user_args[4]);",
    "DEVICE_TYPE_FROM_CTL_CODE(IoControlCode) == 0x47",
    "if (!proc->file_open_devapi_cmapi)",
    "CM_Set_DevNode_Property",
    "CM_Disable_DevNode",
    "CM_Query_And_Remove_SubTree",
    "CM_Register_Device_Interface",
    "CM_Uninstall_DevNode",
    "Log_Debug_Msg(mon_type, msg_str, L\"\\\\Device\\\\DeviceApi\\\\CMApi\");",
    "return NtDeviceIoControlFile(",
    "(PIO_STATUS_BLOCK)user_args[4], // IoStatusBlock",
]:
    require(source, term, "file_ctrl.c")

if source.count("return File_DenyDeviceIoControlFile((PIO_STATUS_BLOCK)user_args[4]);") != 2:
    raise SystemExit("SREV-139 failed: blocked paths do not both use completion helper")

source_without_helper = source.replace(
    "    return STATUS_ACCESS_DENIED;\n}\n\n\n_FX NTSTATUS Syscall_DeviceIoControlFile",
    "}\n\n\n_FX NTSTATUS Syscall_DeviceIoControlFile",
)
reject(source_without_helper, "return STATUS_ACCESS_DENIED;", "file_ctrl.c deny paths")

for term in [
    "### SREV-139: DeviceIoControl Deny IoStatus Completion",
    "DEVICEIOCONTROL_DENY_IOSTATUS_COMPLETION",
    "srev-139-deviceiocontrol-deny-iostatus.schema.json",
    "File_DenyDeviceIoControlFile",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-139 schema/source gate passed")
