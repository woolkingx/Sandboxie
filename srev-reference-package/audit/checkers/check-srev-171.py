#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-171 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-171 failed: stale {label} still present")


def section(text: str, start: str, end: str) -> str:
    start_index = text.index(start)
    end_index = text.index(end, start_index)
    return text[start_index:end_index]


schema = json.loads((ROOT / "docs/plan/srev-171-obj-helper-pipe-name-routing.schema.json").read_text())
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-171 failed: schema is not draft-07")
if schema.get("id") != "OBJ_HELPER_PIPE_NAME_ROUTING":
    raise SystemExit("SREV-171 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "obj.c owns both Obj_NtQueryObject and Obj_GetObjectName object name routes",
    "native NtQueryObject ObjectTypeInformation may classify the Object Manager object type",
    "native NtQueryObject ObjectNameInformation is not the owner of pipe or file identity",
    "File handles that may be named pipes are classified through NtQueryVolumeInformationFile FileFsDeviceInformation",
    "FILE_FS_DEVICE_INFORMATION DeviceType equal to FILE_DEVICE_NAMED_PIPE routes name lookup through Obj_GetObjectNameFromDriver",
    "UseDriverObjLookup remains the broader setting that routes all helper lookups through the driver",
    "driver-routed named pipe object name lookup must not fall back to native NtQueryObject ObjectNameInformation",
    "Linux source gate is not Windows named pipe hang reproduction or compatibility proof",
]:
    require(contracts, term, "schema")

obj_c = (ROOT / "Sandboxie/core/dll/obj.c").read_text()
obj_h = (ROOT / "Sandboxie/core/dll/obj.h").read_text()
file_dir_c = (ROOT / "Sandboxie/core/dll/file_dir.c").read_text()
spec = (ROOT / "docs/plan/srev-171-obj-helper-pipe-name-routing.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-171.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "NTSTATUS Obj_GetObjectName(",
    "ULONG Obj_GetObjectType(HANDLE ObjectHandle);",
    "ULONG File_NtQueryObjectName(UNICODE_STRING *ObjectName, ULONG MaxLen);",
    "ULONG Key_NtQueryObjectName(UNICODE_STRING *ObjectName, ULONG MaxLen);",
    "ULONG Ipc_NtQueryObjectName(UNICODE_STRING *ObjectName, ULONG MaxLen);",
]:
    require(obj_h, term, "obj.h exported owner surface")

for term in [
    "static BOOLEAN Obj_IsNamedPipeFileHandle(HANDLE ObjectHandle);",
    "static NTSTATUS Obj_GetObjectNameFromDriver(",
    "static P_NtQueryObject          __sys_NtQueryObject",
    "static P_NtQueryVolumeInformationFile",
    "GetProcAddress(",
    "\"NtQueryVolumeInformationFile\"",
    "#define FILE_DEVICE_NAMED_PIPE 0x00000011",
    "typedef struct _OBJ_FILE_FS_DEVICE_INFORMATION",
    "ULONG DeviceType;",
    "FileFsDeviceInformation",
    "dev_info.DeviceType == FILE_DEVICE_NAMED_PIPE",
    "status = SbieApi_GetFileName(ObjectHandle, NameBuf, &NameLen, NULL);",
]:
    require(obj_c, term, "obj.c shared pipe/device route")

helper = section(obj_c, "_FX NTSTATUS Obj_GetObjectName(", "// Obj_IsNamedPipeFileHandle")
for term in [
    "obj_use_driver_obj_lookup ||",
    "Obj_GetObjectType(ObjectHandle) == OBJ_TYPE_FILE",
    "Obj_IsNamedPipeFileHandle(ObjectHandle)",
    "status = Obj_GetObjectNameFromDriver(ObjectHandle, ObjectName, Length);",
    "status = __sys_NtQueryObject(",
    "ObjectHandle, ObjectNameInformation, ObjectName, *Length, Length);",
]:
    require(helper, term, "Obj_GetObjectName helper routing")
reject(
    helper,
    "if (obj_use_driver_obj_lookup) {\n\n        status = Obj_GetObjectNameFromDriver",
    "helper driver-only gate",
)

hook = section(obj_c, "_FX NTSTATUS Obj_NtQueryObject(", "// Obj_NtQueryVirtualMemory")
for term in [
    "use_driver_name_lookup =",
    "obj_use_driver_obj_lookup || Obj_IsNamedPipeFileHandle(ObjectHandle);",
    "status = Obj_GetObjectNameFromDriver(ObjectHandle, name, &outlen);",
    "if (use_driver_name_lookup)\n            goto finish;",
    "File_NtQueryObjectName(name, maxlen)",
    "Key_NtQueryObjectName(name, maxlen)",
    "Ipc_NtQueryObjectName(name, maxlen)",
]:
    require(hook, term, "Obj_NtQueryObject existing KPATH-003 route")

for term in [
    "SREV-279: FileFsDeviceInformation is enough to classify named-pipe",
    "query does not cross into object-name resolution first.",
    "FileFsDeviceInformation",
    "FILE_DEVICE_NAMED_PIPE",
    "__sys_NtQueryVolumeInformationFile",
    "SbieDll_GetHandlePath",
]:
    require(file_dir_c, term, "file_dir.c named pipe precedent")

for term in [
    "NtQueryObject on a named pipe handle can hang",
    "pending read/write",
    "need to wait on NtQueryObject",
]:
    reject(file_dir_c, term, "file_dir.c stale named-pipe wording")

for term in [
    "### SREV-171: Object Name Helper Pipe Routing",
    "OBJ_HELPER_PIPE_NAME_ROUTING",
    "srev-171-obj-helper-pipe-name-routing.schema.json",
    "Sandboxie/core/dll/obj.c",
    "Obj_GetObjectName",
    "Obj_NtQueryObject",
    "Obj_IsNamedPipeFileHandle",
    "Obj_GetObjectNameFromDriver",
    "FILE_DEVICE_NAMED_PIPE",
    "UseDriverObjLookup",
    "Windows build plus a sandboxed named-pipe repro",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-171 schema/source gate passed")
