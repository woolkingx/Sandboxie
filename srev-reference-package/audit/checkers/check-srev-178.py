#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-178 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-178 failed: {label} still contains {needle!r}")


def assert_before(text: str, label: str, earlier: str, later: str) -> None:
    e = text.find(earlier)
    l = text.find(later)
    if e < 0 or l < 0 or e > l:
        raise SystemExit(f"SREV-178 failed: {label}")


def function_slice(text: str, start: str, end: str) -> str:
    s = text.index(start)
    e = text.index(end, s)
    return text[s:e]


schema = json.loads((ROOT / "docs/plan/srev-178-mountmanager-wire-string-shape.schema.json").read_text())
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-178 failed: schema is not draft-07")
if schema.get("id") != "MOUNTMANAGER_WIRE_STRING_SHAPE":
    raise SystemExit("SREV-178 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "MountManager owns the ImBox broker request string-shape gate",
    "Fixed password[129] fields must contain L'\\0'",
    "Fixed reg_root[MAX_REG_ROOT_LEN] fields must contain L'\\0'",
    "Flexible file_root[1] tails must contain L'\\0' inside MSG_HEADER.length",
    "CreateHandler rejects a terminated create file_root with no backslash",
    "SbieDll_Mount initializes the full outbound IMBOX_MOUNT_REQ including admin_only",
    "SbieDll_Mount rejects BoxKey values that do not fit password[129] before wcscpy",
]:
    require(contracts, term, "schema contracts")

source = (ROOT / "Sandboxie/core/svc/MountManager.cpp").read_text()
wire = (ROOT / "Sandboxie/core/svc/MountManagerWire.h").read_text()
header = (ROOT / "Sandboxie/core/svc/MountManager.h").read_text()
dll_support = (ROOT / "Sandboxie/core/dll/support.c").read_text()
spec = (ROOT / "docs/plan/srev-178-mountmanager-wire-string-shape.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-178.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "bool AcquireBoxRoot(const WCHAR* boxname, const WCHAR* reg_root, const WCHAR* file_root, ULONG session_id);",
    "void LockBoxRoot(const WCHAR* reg_root, ULONG session_id);",
    "void ReleaseBoxRoot(const WCHAR* reg_root, bool force, ULONG session_id);",
    "MSG_HEADER *CreateHandler(MSG_HEADER *msg);",
    "MSG_HEADER *MountHandler(MSG_HEADER *msg);",
    "MSG_HEADER *UnmountHandler(MSG_HEADER *msg);",
    "MSG_HEADER *QueryHandler(MSG_HEADER *msg);",
]:
    require(header, term, "MountManager.h owner surface")

for term in [
    "WCHAR password[128 + 1];",
    "WCHAR file_root[1];",
    "WCHAR reg_root[MAX_REG_ROOT_LEN];",
    "struct tagIMBOX_CREATE_REQ",
    "struct tagIMBOX_MOUNT_REQ",
    "struct tagIMBOX_UNMOUNT_REQ",
    "struct tagIMBOX_QUERY_REQ",
]:
    require(wire, term, "wire shape")

for term in [
    "static bool MountManager_HasTerminator",
    "static bool MountManager_HasMessageTerminator",
    "static bool MountManager_IsValidRegRoot",
    "static bool MountManager_IsValidPassword",
    "static bool MountManager_IsValidFileRoot",
    "for (ULONG i = 0; i < chars; ++i)",
    "if (value[i] == L'\\0')",
    "if (offset >= msg->length)",
    "ULONG available = msg->length - offset;",
    "available / sizeof(WCHAR)",
    "MAX_REG_ROOT_LEN",
    "128 + 1",
]:
    require(source, term, "MountManager source gate")

create_handler = function_slice(source, "MSG_HEADER *MountManager::CreateHandler", "//---------------------------------------------------------------------------\n// MountHandler")
mount_handler = function_slice(source, "MSG_HEADER *MountManager::MountHandler", "//---------------------------------------------------------------------------\n// UnmountHandler")
unmount_handler = function_slice(source, "MSG_HEADER *MountManager::UnmountHandler", "//---------------------------------------------------------------------------\n// EnumHandler")
query_handler = function_slice(source, "MSG_HEADER *MountManager::QueryHandler", "//---------------------------------------------------------------------------\n// UpdateHandler")

for term in [
    "if (!MountManager_IsValidPassword(req->password)",
    "!MountManager_IsValidFileRoot(&req->h, req->file_root))",
    "const WCHAR* RootEnd = wcsrchr(req->file_root, L'\\\\');",
    "if (!RootEnd)",
    "return SHORT_REPLY(ERROR_INVALID_PARAMETER);",
    "std::wstring RootPath(req->file_root, RootEnd - req->file_root);",
]:
    require(create_handler, term, "CreateHandler gate")
assert_before(create_handler, "CreateHandler password gate before GetImageFileName",
              "MountManager_IsValidPassword(req->password)",
              "std::wstring ImageFile = GetImageFileName(req->file_root);")
assert_before(create_handler, "CreateHandler file_root gate before wcsrchr",
              "MountManager_IsValidFileRoot(&req->h, req->file_root)",
              "wcsrchr(req->file_root, L'\\\\')")
assert_before(create_handler, "CreateHandler RootEnd null gate before RootPath range",
              "if (!RootEnd)",
              "std::wstring RootPath(req->file_root, RootEnd - req->file_root);")
reject(create_handler, "std::wstring RootPath(req->file_root, wcsrchr", "unchecked create root range")
reject(create_handler, "std::wstring RootPath(req->file_root, RootEnd);", "ambiguous create root iterator range")

for term in [
    "MountManager_IsValidPassword(req->password)",
    "MountManager_IsValidRegRoot(req->reg_root)",
    "MountManager_IsValidFileRoot(&req->h, req->file_root)",
]:
    require(mount_handler, term, "MountHandler gate")
assert_before(mount_handler, "MountHandler gate before GetImageFileName",
              "MountManager_IsValidFileRoot(&req->h, req->file_root)",
              "std::wstring ImageFile = GetImageFileName(req->file_root);")
assert_before(mount_handler, "MountHandler reg gate before protect",
              "MountManager_IsValidRegRoot(req->reg_root)",
              "SbieApi_Call(API_PROTECT_ROOT")

require(unmount_handler, "MountManager_IsValidRegRoot(req->reg_root)", "UnmountHandler reg gate")
assert_before(unmount_handler, "UnmountHandler reg gate before map lookup",
              "MountManager_IsValidRegRoot(req->reg_root)",
              "GetBoxRootLocked(req->reg_root")

require(query_handler, "MountManager_IsValidRegRoot(req->reg_root)", "QueryHandler reg gate")
assert_before(query_handler, "QueryHandler reg gate before dereference",
              "MountManager_IsValidRegRoot(req->reg_root)",
              "if (*req->reg_root)")

mount_api = function_slice(dll_support, "_FX BOOLEAN SbieDll_Mount", "//---------------------------------------------------------------------------\n// SbieDll_Unmount")
for term in [
    "memzero(req, req_len);",
    "if (BoxKey && wcslen(BoxKey) >= ARRAYSIZE(req->password))",
    "Dll_Free(req);",
    "return FALSE;",
    "if (BoxKey)",
    "wcscpy(req->password, BoxKey);",
    "req->protect_root = Protect;",
    "req->auto_unmount = FALSE;",
]:
    require(mount_api, term, "SbieDll_Mount")
assert_before(mount_api, "request zero before field writes",
              "memzero(req, req_len);",
              "req->h.length = req_len;")
assert_before(mount_api, "BoxKey bound before wcscpy",
              "if (BoxKey && wcslen(BoxKey) >= ARRAYSIZE(req->password))",
              "wcscpy(req->password, BoxKey);")

for term in [
    "kind: srev-ledger-entry",
    "id: SREV-178",
    "owner: MountManager broker wire request boundary",
    "checker: docs/plan/check-srev-178.py",
]:
    require(ledger_fragment, term, "ledger fragment header")

for term in [
    "### SREV-178: MountManager Wire String Shape",
    "MOUNTMANAGER_WIRE_STRING_SHAPE",
    "Sandboxie/core/svc/MountManager.h",
    "Sandboxie/core/svc/MountManagerWire.h",
    "Sandboxie/core/svc/MountManager.cpp",
    "Sandboxie/core/dll/support.c",
    "MountManager_HasMessageTerminator",
    "SbieDll_Mount",
    "BoxKey",
    "admin_only",
]:
    require(ledger, term, "ledger")

print("SREV-178 schema/source gate passed")
