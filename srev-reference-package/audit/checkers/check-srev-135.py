#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-135 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-135 failed: {label} still contains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-135-mountmanager-reparse-buffer-and-query-defaults.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-135 failed: schema is not draft-07")
if schema.get("id") != "MOUNTMANAGER_REPARSE_BUFFER_AND_QUERY_DEFAULTS":
    raise SystemExit("SREV-135 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "ImDiskOpenDeviceByMountPoint treats FSCTL_GET_REPARSE_POINT output as untrusted counted data",
    "HeapAlloc failure returns INVALID_HANDLE_VALUE without raising HEAP_GENERATE_EXCEPTIONS through the service helper",
    "ReparseDataLength is bounded by the bytes DeviceIoControl reports before MountPointReparseBuffer fields are trusted",
    "MountPointReparseBuffer substitute-name offset and length are WCHAR-aligned",
    "MountPointReparseBuffer substitute-name offset plus length stays inside returned PathBuffer bytes",
    "Zero-length substitute names are rejected before trailing-slash trimming indexes the buffer",
    "Valid mount-point substitute names still flow to ImDiskOpenDeviceByName with existing trailing-slash trimming",
    "ImDiskQueryDeviceSize returns zero when the device cannot be opened or queried as an ImDisk proxy device",
]:
    require(contracts, term, "schema")

source = (ROOT / "Sandboxie/core/svc/MountManagerHelpers.cpp").read_text()
ntddk = (ROOT / "Sandboxie/common/win32_ntddk.h").read_text()
spec = (ROOT / "docs/plan/srev-135-mountmanager-reparse-buffer-and-query-defaults.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-135.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "typedef struct _REPARSE_DATA_BUFFER",
    "USHORT ReparseDataLength;",
    "USHORT SubstituteNameOffset;",
    "USHORT SubstituteNameLength;",
    "WCHAR  PathBuffer[1];",
    "} MountPointReparseBuffer;",
]:
    require(ntddk, term, "local REPARSE_DATA_BUFFER")

mount_helper = source[
    source.index("HANDLE WINAPI ImDiskOpenDeviceByMountPoint"):
    source.index("BOOL WINAPI IsImDiskDriverReady")
]
for term in [
    "HeapAlloc(GetProcessHeap(),",
    "HEAP_ZERO_MEMORY,",
    "if (!ReparseData)",
    "CloseHandle(hDir);",
    "SetLastError(ERROR_NOT_ENOUGH_MEMORY);",
    "DeviceIoControl(hDir, FSCTL_GET_REPARSE_POINT",
    "const DWORD reparse_header_size =",
    "FIELD_OFFSET(REPARSE_DATA_BUFFER, MountPointReparseBuffer);",
    "const DWORD mount_path_header_size =",
    "FIELD_OFFSET(REPARSE_DATA_BUFFER, MountPointReparseBuffer.PathBuffer) -",
    "const DWORD returned_data_size =",
    "(dw >= reparse_header_size) ? dw - reparse_header_size : 0;",
    "const DWORD path_data_size =",
    "const USHORT substitute_name_offset =",
    "const USHORT substitute_name_length =",
    "(dw < reparse_header_size + mount_path_header_size)",
    "(ReparseData->ReparseDataLength < mount_path_header_size)",
    "(ReparseData->ReparseDataLength > returned_data_size)",
    "(substitute_name_length == 0)",
    "((substitute_name_offset | substitute_name_length) & (sizeof(WCHAR) - 1))",
    "((DWORD)substitute_name_offset + substitute_name_length > path_data_size)",
    "SetLastError(ERROR_INVALID_DATA);",
    "DeviceName.Length =",
    "substitute_name_length;",
    "DeviceName.Buffer = (PWSTR)",
    "substitute_name_offset);",
    "if (DeviceName.Length &&",
    "ImDiskOpenDeviceByName(&DeviceName, AccessMode);",
]:
    require(mount_helper, term, "ImDiskOpenDeviceByMountPoint")

reject(mount_helper, "HEAP_GENERATE_EXCEPTIONS", "MountManager helper heap allocation")
reject(mount_helper, "if (DeviceName.Buffer[(DeviceName.Length >> 1) - 1] == L'\\\\')", "unguarded trailing-slash trim")

if mount_helper.index("if (!ReparseData)") > mount_helper.index("DeviceIoControl(hDir, FSCTL_GET_REPARSE_POINT"):
    raise SystemExit("SREV-135 failed: allocation result is checked after DeviceIoControl")
if mount_helper.index("const DWORD reparse_header_size") > mount_helper.index("DeviceName.Length ="):
    raise SystemExit("SREV-135 failed: reparse size gates are after DeviceName construction")
if mount_helper.index("(substitute_name_length == 0)") > mount_helper.index("if (DeviceName.Length &&"):
    raise SystemExit("SREV-135 failed: zero-length gate is after trailing-slash guard")
if mount_helper.index("SetLastError(ERROR_NOT_A_REPARSE_POINT);") > mount_helper.index("const DWORD reparse_header_size"):
    raise SystemExit("SREV-135 failed: non-mount-point tag no longer exits before mount buffer interpretation")

query_size = source[
    source.index("ULONGLONG ImDiskQueryDeviceSize"):
]
for term in [
    "ULONGLONG size = 0;",
    "if (DeviceIoControl(device, IOCTL_IMDISK_QUERY_DEVICE",
    "if (IMDISK_TYPE(u.create_data.Flags) == IMDISK_TYPE_PROXY)",
    "size = u.create_data.DiskGeometry.Cylinders.QuadPart;",
    "return size;",
]:
    require(query_size, term, "ImDiskQueryDeviceSize")

for term in [
    "kind: srev-ledger-entry",
    "id: SREV-135",
    "owner: Sandboxie/core/svc/MountManagerHelpers.cpp",
    "checker: docs/plan/check-srev-135.py",
]:
    require(ledger_fragment, term, "ledger fragment header")

for term in [
    "### SREV-135: MountManager Reparse Buffer And Query Defaults",
    "MOUNTMANAGER_REPARSE_BUFFER_AND_QUERY_DEFAULTS",
    "srev-135-mountmanager-reparse-buffer-and-query-defaults.schema.json",
    "Sandboxie/core/svc/MountManagerHelpers.cpp",
    "Sandboxie/common/win32_ntddk.h",
    "ImDiskOpenDeviceByMountPoint",
    "ImDiskQueryDeviceSize",
    "FSCTL_GET_REPARSE_POINT",
    "REPARSE_DATA_BUFFER",
    "DeviceIoControl",
    "HeapAlloc",
    "HEAP_GENERATE_EXCEPTIONS",
    "ERROR_INVALID_DATA",
]:
    require(ledger, term, "ledger")

print("SREV-135 schema/source gate passed")
