#!/usr/bin/env python3
import json
import re
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-176 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-176 failed: stale {label} still present")


def function_body(text: str, name: str) -> str:
    match = re.search(rf"\b{name}\s*\([^)]*\)\s*\{{", text, re.S)
    if not match:
        raise SystemExit(f"SREV-176 failed: function {name} missing")
    start = match.end() - 1
    depth = 0
    for index in range(start, len(text)):
        char = text[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start:index + 1]
    raise SystemExit(f"SREV-176 failed: function {name} body not closed")


schema = json.loads((ROOT / "docs/plan/srev-176-key-util-registry-path-shape.schema.json").read_text())
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-176 failed: schema is not draft-07")
if schema.get("id") != "KEY_UTIL_REGISTRY_PATH_SHAPE":
    raise SystemExit("SREV-176 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "Key_GetName owns key path normalization for RootDirectory plus UNICODE_STRING ObjectName",
    "Key_OpenIfBoxed must not create a second registry path builder from KEY_NAME_INFORMATION",
    "Key_OpenIfBoxed calls SbieDll_MatchPath on the NUL-terminated true path returned by Key_GetName",
    "Key_OpenIfBoxed preserves the existing PATH_WRITE_FLAG gate and STATUS_BAD_INITIAL_PC deny status",
    "Key_OpenOrCreateIfBoxed saves and restores SecurityDescriptor with the same pointer level as OBJECT_ATTRIBUTES SecurityDescriptor",
    "Key_DeleteValueFromCLSID allocates storage from measured prefix class GUID braces slash and terminator then frees it before return",
    "SREV-176 does not change the registry policy model custom app behavior CLSID value names WOW64 access flags or create-on-missing behavior",
    "Linux source gate is not Windows DLL build runtime proof",
]:
    require(contracts, term, "schema")

key_util = (ROOT / "Sandboxie/core/dll/key_util.c").read_text()
key_c = (ROOT / "Sandboxie/core/dll/key.c").read_text()
spec = (ROOT / "docs/plan/srev-176-key-util-registry-path-shape.md").read_text()
coordinate = (ROOT / "docs/plan/sandboxie-isolation-coordinate.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-176.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

require(key_util, "#include <limits.h>", "ULONG_MAX header owner")
require(key_c, "SBIEDLL_EXPORT NTSTATUS Key_GetName(", "Key_GetName owner")
require(key_c, '#include "key_util.c"', "key_util include topology")

open_body = function_body(key_util, "Key_OpenIfBoxed")
require(open_body, "Key_GetName(", "Key_OpenIfBoxed owner call")
require(open_body, "objattrs->RootDirectory", "Key_OpenIfBoxed root input")
require(open_body, "objattrs->ObjectName", "Key_OpenIfBoxed object input")
require(open_body, "SbieDll_MatchPath(L'k', TruePath)", "Key_OpenIfBoxed path gate")
require(open_body, "PATH_WRITE_FLAG", "Key_OpenIfBoxed write flag gate")
require(open_body, "STATUS_BAD_INITIAL_PC", "Key_OpenIfBoxed deny status")
require(open_body, "NtOpenKey(out_handle, access, objattrs)", "Key_OpenIfBoxed native open")
reject(open_body, "KEY_NAME_INFORMATION", "private key-name builder")
reject(open_body, "NtQueryKey", "private NtQueryKey path query")
reject(open_body, "Dll_Alloc(", "manual root path allocation")
reject(open_body, "wcscpy", "NUL-terminated object-name copy")

create_body = function_body(key_util, "Key_OpenOrCreateIfBoxed")
require(create_body, "PSECURITY_DESCRIPTOR SaveSD = objattrs->SecurityDescriptor;", "SecurityDescriptor save pointer level")
require(create_body, "objattrs->SecurityDescriptor = Secure_EveryoneSD;", "temporary SD override")
require(create_body, "objattrs->SecurityDescriptor = SaveSD;", "SecurityDescriptor restore")
reject(create_body, "PSECURITY_DESCRIPTOR *SaveSD", "stale SecurityDescriptor pointer-to-pointer save")

delete_body = function_body(key_util, "Key_DeleteValueFromCLSID")
require(delete_body, 'L"\\\\registry\\\\machine\\\\software\\\\classes\\\\"', "HKLM classes prefix")
require(delete_body, "SIZE_T path_len;", "measured path length type")
require(delete_body, "wcslen(_HKLM_Classes) + wcslen(Xxxid) + wcslen(Guid) + 4", "path length formula")
require(delete_body, "ULONG_MAX / sizeof(WCHAR)", "ULONG allocation bound")
require(delete_body, "Dll_AllocTemp((ULONG)(path_len * sizeof(WCHAR)))", "measured allocation")
require(delete_body, "if (! path)", "allocation failure gate")
require(delete_body, 'Sbie_snwprintf(path, path_len, L"%s%s\\\\{%s}"', "bounded path format")
require(delete_body, "Dll_Free(path);", "path free")
reject(delete_body, "128 * sizeof(WCHAR)", "fixed CLSID path buffer")
reject(delete_body, "wcscpy(path", "fixed path copy")
reject(delete_body, "wcscat(path", "fixed path append")

for term in [
    "host-readable",
    "sandbox-writable",
    "fresh-machine",
    "custom-exception",
    "read host -> write sandbox copy",
]:
    require(coordinate, term, "isolation coordinate")
    require(spec, "sandboxie-isolation-coordinate.md", "spec coordinate link")

for term in [
    "### SREV-176: Key Utility Registry Path Shape",
    "KEY_UTIL_REGISTRY_PATH_SHAPE",
    "srev-176-key-util-registry-path-shape.schema.json",
    "Sandboxie/core/dll/key_util.c",
    "Key_OpenIfBoxed",
    "Key_DeleteValueFromCLSID",
    "Windows DLL build",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-176 schema/source gate passed")
