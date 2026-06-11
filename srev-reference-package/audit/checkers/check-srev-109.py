#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-109 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-109 failed: {label} still contains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-109-mountmanager-imbox-state-boundaries.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-109 failed: schema is not draft-07")
if schema.get("id") != "MOUNTMANAGER_IMBOX_STATE_BOUNDARIES":
    raise SystemExit("SREV-109 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "constructor does not rebuild m_RootMap from devices alone",
    "FindImDisk recovers only ImDisk device identity by proxy name",
    "reg_root and file_root ownership comes from IMBOX_MOUNT or AcquireBoxRoot requests",
    "BOX_MOUNT Protected becomes true only after API_PROTECT_ROOT succeeds",
    "recovered ImDisk devices do not imply protected-root state",
    "IMBOX_UPDATE remains unsupported",
    "temporary drive-letter path",
    "unrequested drive-letter mappings are removed",
    "BoxPassword is not read from durable config",
    "caller-supplied password",
    "FSCTL_SET_REPARSE_POINT",
    "FSCTL_DELETE_REPARSE_POINT",
    "DefineDosDeviceW removes exact raw target mappings",
]:
    require(contracts, term, "schema")

source = (ROOT / "Sandboxie/core/svc/MountManager.cpp").read_text()
header = (ROOT / "Sandboxie/core/svc/MountManager.h").read_text()
wire = (ROOT / "Sandboxie/core/svc/MountManagerWire.h").read_text()
support = (ROOT / "Sandboxie/core/dll/support.c").read_text()
spec = (ROOT / "docs/plan/srev-109-mountmanager-imbox-state-boundaries.md").read_text()
ledger = read_combined_ledger(ROOT)

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for stale in [
    "todo: find mounted disks",
    "ERROR_CALL_NOT_IMPLEMENTED); // todo",
    "pMount->Protected = todo: query driver",
    "todo allow mounting without mount",
    "BoxPassword\", 0, Password, sizeof(Password)); // todo",
]:
    reject(source, stale, "MountManager.cpp")

for term in [
    "Existing ImBox devices are rediscovered lazily by FindImDisk",
    "constructor does not rebuild m_RootMap from devices alone",
    "Image resize and password rotation need an ImBox update transaction",
    "return SHORT_REPLY(ERROR_CALL_NOT_IMPLEMENTED);",
    "Recovered devices do not carry the request reg_root/admin_only owner",
    "Protection is restored only by an explicit API_PROTECT_ROOT mount path",
    "ImBox formats through the temporary drive-letter path",
    "remove the DOS-device mapping after discovery",
    "Do not read a durable BoxPassword here",
    "caller-supplied passwords until a secure credential handoff exists",
]:
    require(source, term, "MountManager.cpp boundary comments")

for term in [
    "struct BOX_MOUNT",
    "bool Protected = false;",
    "struct BOX_ROOT",
    "MountManager::MountHandler",
    "FindImDisk(ImageFile, session_id)",
    "MountImDisk(ImageFile, req->password",
    "API_PROTECT_ROOT",
    "pMount->Protected = true;",
    "CreateJunction(TargetNtPath, req->file_root",
    "MountManager::UpdateHandler",
    "MountManager::FindImDisk",
    "ImDiskGetDeviceListEx",
    "ImDiskQueryDeviceProxy",
    "pMount->NtPath = TargetNtPath;",
    "MountManager::MountImDisk",
    "GetLogicalDrives()",
    "ImDiskFindFreeDriveLetter()",
    "cmd += L\" size=\"",
    "cmd += L\" proxy=\" IMBOX_PROXY",
    "AllocPasswordMemory(pi.hProcess, pPassword)",
    "DefineDosDevice(DDD_REMOVE_DEFINITION | DDD_EXACT_MATCH_ON_REMOVE | DDD_RAW_TARGET_PATH",
    "MountManager::AcquireBoxRoot",
    "UseFileImage",
    "UseRamDisk",
    "SbieApi_QueryDrvInfo(-1, &CertInfo",
    "MountImDisk(ImageFile, NULL",
    "RemoveJunction",
    "FSCTL_SET_REPARSE_POINT",
    "FSCTL_DELETE_REPARSE_POINT",
]:
    require(source, term, "MountManager.cpp topology")

require(header, "std::map<std::wstring, std::shared_ptr<BOX_ROOT> > m_RootMap;", "MountManager.h topology")

for term in [
    "IMBOX_MOUNT_REQ",
    "WCHAR password[128 + 1];",
    "BOOL protect_root;",
    "BOOL admin_only;",
    "BOOL auto_unmount;",
    "WCHAR reg_root[MAX_REG_ROOT_LEN];",
    "IMBOX_UPDATE_REQ",
    "WCHAR new_password[128 + 1];",
    "ULONG64 new_image_size;",
]:
    require(wire, term, "MountManagerWire.h wire shape")

for term in [
    "SbieDll_Mount",
    "wcscpy(req->password, BoxKey);",
    "req->protect_root = Protect;",
    "req->auto_unmount = FALSE;",
    "MSGID_IMBOX_MOUNT",
]:
    require(support, term, "support.c request credential shape")

for term in [
    "### SREV-109: MountManager ImBox State Boundaries",
    "MOUNTMANAGER_IMBOX_STATE_BOUNDARIES",
    "srev-109-mountmanager-imbox-state-boundaries.schema.json",
    "Sandboxie/core/svc/MountManager.cpp",
    "FindImDisk",
    "API_PROTECT_ROOT",
    "BoxPassword",
]:
    require(ledger, term, "ledger")

print("SREV-109 schema/source gate passed")
