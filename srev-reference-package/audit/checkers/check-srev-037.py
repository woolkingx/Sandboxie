#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-037 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-037 failed: {label} still contains {needle!r}")


schema = json.loads((ROOT / "docs/plan/srev-037-ipc-create-dir-link-wire.schema.json").read_text())
if schema.get("id") != "IPC_CREATE_DIR_OR_LINK_COUNTED_STRING":
    raise SystemExit("SREV-037 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "UNICODE_STRING64.Length is a byte count",
    "UNICODE_STRING64.Length must be at least one WCHAR, < 2048 bytes, and <= MaximumLength",
    "embedded NUL is invalid before RtlInitUnicodeString",
    "objname must be boxed before creating the directory or symbolic link object, except for the same-box BNOLINKS bootstrap auxiliary subtree",
    "target must be boxed before creating a symbolic link object, except for the same-box BNOLINKS bootstrap auxiliary subtree",
    "either stored in Ipc_ObjDirs or closed before return",
]:
    require(contracts, term, "schema")

src = (ROOT / "Sandboxie/core/drv/ipc.c").read_text()
spec = (ROOT / "docs/plan/srev-037-ipc-create-dir-link-wire.md").read_text()
ledger = read_combined_ledger(ROOT)

start = src.index("_FX NTSTATUS Ipc_Api_CreateDirOrLink(")
end = src.index("// Ipc_Api_OpenDeviceMap", start)
create = src[start:end]

for term in [
    "static BOOLEAN Ipc_Api_CreateDirOrLinkContainsWChar(",
    "static NTSTATUS Ipc_Api_CreateDirOrLinkCopyString(",
    "user_len = user_uni->Length;",
    "(user_len & (sizeof(WCHAR) - 1))",
    "(user_uni->MaximumLength < user_len)",
    "Ipc_Api_CreateDirOrLinkContainsWChar(buf, user_len, L'\\0')",
    "buf[user_len / sizeof(WCHAR)] = L'\\0';",
]:
    require(src, term, "copy helper")

for term in [
    "status = Ipc_Api_CreateDirOrLinkCopyString(\n        proc, user_uni, &objname_buf, &objname_len);",
    "status = Ipc_Api_CreateDirOrLinkCopyString(\n            proc, user_uni, &target_buf, &target_len);",
    "RtlInitUnicodeString(&objname, objname_buf);",
    "Ipc_Api_CreateDirOrLinkIsBoxedPath(proc->box, &objname)",
    "RtlInitUnicodeString(&target, target_buf);",
    "Ipc_Api_CreateDirOrLinkIsBoxedPath(proc->box, &target)",
    "DIR_OBJ_HANDLE *obj_handle = Mem_Alloc(Driver_Pool, sizeof(DIR_OBJ_HANDLE));",
    "if (obj_handle) {",
    "ZwClose(handle);\n            status = STATUS_INSUFFICIENT_RESOURCES;",
]:
    require(create, term, "Ipc_Api_CreateDirOrLink")

for term in [
    "static BOOLEAN Ipc_Api_CreateDirOrLinkIsBnolinksPath(",
    "static BOOLEAN Ipc_Api_CreateDirOrLinkIsBoxedPath(",
    "Box_IsBoxedPath(box, ipc, uni)",
    "Ipc_Api_CreateDirOrLinkIsBnolinksPath(box, uni)",
]:
    require(src, term, "Ipc_Api_CreateDirOrLink helper")

reject(create, "user_len & ~1", "Ipc_Api_CreateDirOrLink")
reject(create, "obj_handle->handle = handle;\n        List_Insert_After", "Ipc_Api_CreateDirOrLink")

for term in [
    "https://learn.microsoft.com/en-us/windows/win32/api/ntdef/ns-ntdef-_unicode_string",
    "https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-rtlinitunicodestring",
    "https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-zwcreatedirectoryobject",
    "https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-iocreatesymboliclink",
    "same-box `BNOLINKS` bootstrap subtree",
    "srev-037-ipc-create-dir-link-wire.schema.json",
]:
    require(spec, term, "spec")

for term in [
    "### SREV-037: IPC Create Directory Or Link Counted String",
    "Ipc_Api_CreateDirOrLinkCopyString",
    "srev-037-ipc-create-dir-link-wire.schema.json",
]:
    require(ledger, term, "ledger")

print("SREV-037 schema/source gate passed")
