#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-279 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-279 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-279-volume-device-info-named-pipe-fast-path.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-279 failed: schema is not draft-07")
if schema.get("id") != "VOLUME_DEVICE_INFO_NAMED_PIPE_FAST_PATH":
    raise SystemExit("SREV-279 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/dll/file_dir.c":
    raise SystemExit("SREV-279 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "named-pipe FileFsDeviceInformation fast path",
    "output shape is selected by FsInformationClass",
    "FileFsDeviceInformation returns FILE_FS_DEVICE_INFORMATION",
    "DeviceType identifies the associated device object type",
    "FILE_DEVICE_NAMED_PIPE is enough to answer this volume-info query",
    "must not route through object-name resolution",
    "Recursive File_NtQueryVolumeInformationFile calls while the hook is already translating a handle path must use the native volume-info owner directly",
    "KnownDll sandbox probing must not let volume-info queries recurse through SbieDll_GetHandlePath",
    "KPATH-003 and SREV-171 own broader object-name routing",
    "this SREV owns the volume-info fast path and reentrancy gate",
]:
    require(contracts, term, "schema")

src = (ROOT / "Sandboxie/core/dll/file_dir.c").read_text()
spec = (ROOT / "docs/plan/srev-279-volume-device-info-named-pipe-fast-path.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-279.md").read_text()

start = src.index("_FX NTSTATUS File_NtQueryVolumeInformationFile(")
end = src.index("if (! NT_SUCCESS(status))", start)
volume = src[start:end]

for term in [
    "THREAD_DATA *TlsData = Dll_GetTlsData(NULL);",
    "TlsData->ipc_KnownDlls_lock",
    "TlsData->file_NtQueryVolumeInformation_lock",
    "FileHandle, IoStatusBlock, FsInformation, Length, FsInformationClass",
    "SREV-279: FileFsDeviceInformation is enough to classify named-pipe",
    "handles.  Return that device-info result directly so this volume-info",
    "query does not cross into object-name resolution first.",
    "FsInformationClass == FileFsDeviceInformation",
    "Length >= sizeof(FILE_FS_DEVICE_INFORMATION)",
    "FILE_FS_DEVICE_INFORMATION devInfo = { 0 };",
    "__sys_NtQueryVolumeInformationFile(FileHandle, &ioStatusBlock, &devInfo, sizeof(devInfo), FileFsDeviceInformation)",
    "devInfo.DeviceType == FILE_DEVICE_NAMED_PIPE",
    "*IoStatusBlock = ioStatusBlock;",
    "memcpy(FsInformation, &devInfo, sizeof(devInfo));",
    "return status;",
]:
    require(volume, term, "volume-info source block")

require(
    (ROOT / "Sandboxie/core/dll/dll.h").read_text(),
    "BOOLEAN file_NtQueryVolumeInformation_lock;",
    "thread-data lock",
)

for stale in [
    "NtQueryObject on a named pipe handle can hang",
    "pending read/write",
    "need to wait on NtQueryObject",
]:
    reject(volume, stale, "named-pipe volume-info stale comment")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for path, terms in {
    "docs/plan/2026-05-27-sandboxie-kernel-path-audit.md": ["KPATH-003", "FILE_DEVICE_NAMED_PIPE"],
    "docs/plan/ledger/srev-171.md": ["SREV-171", "Obj_IsNamedPipeFileHandle", "FILE_DEVICE_NAMED_PIPE"],
}.items():
    text = (ROOT / path).read_text()
    for term in terms:
        require(text, term, path)

for term in [
    "### SREV-279: Volume Device Info Named-Pipe Fast Path",
    "VOLUME_DEVICE_INFO_NAMED_PIPE_FAST_PATH",
    "srev-279-volume-device-info-named-pipe-fast-path.schema.json",
    "Sandboxie/core/dll/file_dir.c",
    "FileFsDeviceInformation",
    "FILE_DEVICE_NAMED_PIPE",
    "file_NtQueryVolumeInformation_lock",
    "SREV-171",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-279 source gate passed")
