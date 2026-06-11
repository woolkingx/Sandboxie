#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-337 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-337 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-337-key-mount-hive-devicemap-warmup.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-337 failed: schema is not draft-07")
if schema.get("id") != "KEY_MOUNT_HIVE_DEVICEMAP_WARMUP":
    raise SystemExit("SREV-337 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/drv/key.c":
    raise SystemExit("SREV-337 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "pre-ZwLoadKey current-process DosDevices device-map warmup ordering",
    "Windows object manager namespace",
    "drive-letter presentation context-sensitive",
    "ObOpenObjectByName opens an object by name with validation and auditing",
    "drive letter is incidental and the volume need not exist",
    "ZwLoadKey owns the registry hive load",
    "token default-DACL save replace restore ordering",
    "this SREV changes comments and proof only",
]:
    require(contracts, term, "schema")

key = (ROOT / "Sandboxie/core/drv/key.c").read_text()
spec = (ROOT / "docs/plan/srev-337-key-mount-hive-devicemap-warmup.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-337.md").read_text()
srev_026 = (ROOT / "docs/plan/ledger/srev-026.md").read_text()
srev_111 = (ROOT / "docs/plan/ledger/srev-111.md").read_text()
srev_008 = (ROOT / "docs/plan/ledger/srev-008.md").read_text()
srev_233 = (ROOT / "docs/plan/ledger/srev-233.md").read_text()
srev_280 = (ROOT / "docs/plan/ledger/srev-280.md").read_text()

mount2_start = key.index("_FX BOOLEAN Key_MountHive2(PROCESS *proc, KEY_MOUNT *mount)")
mount2_end = key.index("// Key_MountHive3", mount2_start)
mount2 = key[mount2_start:mount2_end]

mount3_start = key.index("_FX BOOLEAN Key_MountHive3(")
mount3_end = key.index("// Key_MountHive4", mount3_start)
mount3 = key[mount3_start:mount3_end]

for term in [
    "if (proc->in_app_pkg){",
    "return Key_MountHive4(proc, &target, &source);",
    "return Key_MountHive3(proc, &target, &source);",
]:
    require(mount2, term, "Key_MountHive2 routing")

for term in [
    "old_token_dacl =\n        Token_QueryPrimary(TokenDefaultDacl, proc->box->session_id);",
    "ZwOpenProcessTokenEx(\n            NtCurrentProcess(), TOKEN_QUERY | TOKEN_ADJUST_DEFAULT,\n            OBJ_KERNEL_HANDLE, &token)",
    "new_token_dacl.DefaultDacl = Driver_PublicAcl;",
    "ZwSetInformationToken(token, TokenDefaultDacl,\n                                           &new_token_dacl,",
    "RtlInitUnicodeString(&uni, L\"\\\\??\\\\C:\");",
    "InitializeObjectAttributes(&objattrs,\n                    &uni, OBJ_CASE_INSENSITIVE | OBJ_KERNEL_HANDLE, NULL, NULL);",
    "SREV-337: warm the current process DosDevices/device-map",
    "context before ZwLoadKey resolves a hive source path.",
    "drive letter is only a trigger; the volume need not exist.",
    "ObOpenObjectByName(\n                    &objattrs, *IoFileObjectType, KernelMode, NULL, 0, NULL, &handle)",
    "ZwClose(handle);",
    "status = ZwLoadKey(target, source);",
    "Api_SendServiceMessage(SVC_MOUNTED_HIVE, sizeof(msg), &msg);",
    "ZwSetInformationToken(token, TokenDefaultDacl,\n                                                old_token_dacl,",
    "ExFreePool(old_token_dacl);",
]:
    require(mount3, term, "Key_MountHive3 block")

for stale in [
    "ZwLoadKey can fail with device path if current process's devicemap is null",
    "One workaround is to call ObOpenObjectByName and it will trigger devicemap",
    "Using C: is not necessary",
    "\\\\??\\\\A:",
]:
    reject(mount3, stale, "Key_MountHive3 comment")

if not mount3.index("ObOpenObjectByName(") < mount3.index("status = ZwLoadKey(target, source);"):
    raise SystemExit("SREV-337 failed: warmup is not before ZwLoadKey")
if not mount3.index("new_token_dacl.DefaultDacl = Driver_PublicAcl;") < mount3.index("ObOpenObjectByName("):
    raise SystemExit("SREV-337 failed: public DACL replacement is not before warmup")
if not mount3.index("status = ZwLoadKey(target, source);") < mount3.index("old_token_dacl,"):
    raise SystemExit("SREV-337 failed: DACL restore is not after ZwLoadKey")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "NtLoadKey",
    "FILE_LOAD_KEY_PATH_CHARS",
    "TrustedInstaller LoadKey runtime proof",
]:
    require(srev_026, term, "SREV-026 adjacency")

for term in [
    "TOKEN_DEFAULT_DACL",
    "GetTokenInformation",
    "SetTokenInformation",
]:
    require(srev_008, term, "SREV-008 adjacency")

for term in [
    "Driver_PublicAcl",
    "Driver_InitPublicSecurity",
]:
    require(srev_111, term, "SREV-111 adjacency")

for term in [
    "Key_MountHive",
    "Key_InitProcess",
    "key.c",
]:
    require(srev_233, term, "SREV-233 adjacency")

for term in [
    "local and global DosDevices contexts",
    "MS-DOS device names are object-namespace junctions",
    "QueryDosDevice",
]:
    require(srev_280, term, "SREV-280 adjacency")

for term in [
    "### SREV-337: Key Mount Hive Device-Map Warmup",
    "KEY_MOUNT_HIVE_DEVICEMAP_WARMUP",
    "srev-337-key-mount-hive-devicemap-warmup.schema.json",
    "Sandboxie/core/drv/key.c",
    "Key_MountHive3",
    "ObOpenObjectByName",
    "ZwLoadKey",
    "TokenDefaultDacl",
    "SREV-008",
    "SREV-026",
    "SREV-111",
    "SREV-233",
    "SREV-280",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-337 source gate passed")
