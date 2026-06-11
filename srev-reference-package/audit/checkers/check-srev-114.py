#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-114 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-114 failed: {label} still contains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-114-scm-service-key-path-shape.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-114 failed: schema is not draft-07")
if schema.get("id") != "SCM_SERVICE_KEY_PATH_SHAPE":
    raise SystemExit("SREV-114 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "OpenServiceW service names are non-empty and at most 256 characters",
    "tzuk marker followed by the service-name payload",
    "lower-casing applies only to the service-name payload",
    "Scm_ServicesKeyPath slash and service name",
    "sized from actual base path and service name length",
    "Scm_OpenKeyForService owns the temporary path buffer",
    "Scm_DiscardKeyCache invalidates Services root and service subkey",
]:
    require(contracts, term, "schema")

source = (ROOT / "Sandboxie/core/dll/scm.c").read_text()
spec = (ROOT / "docs/plan/srev-114-scm-service-key-path-shape.md").read_text()
ledger = read_combined_ledger(ROOT)

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

require(source, "static WCHAR *Scm_AllocServiceKeyPath(const WCHAR *ServiceName);", "helper prototype")

open_start = source.index("_FX SC_HANDLE Scm_OpenServiceWImpl(")
open_end = source.index("// Scm_HookOpenServiceW", open_start)
open_impl = source[open_start:open_end]

for term in [
    "if (wcslen(lpServiceName) > SCM_SERVICE_NAME_MAX_CHARS)",
    "SetLastError(ERROR_INVALID_NAME);",
    "Scm_DiscardKeyCache(lpServiceName);",
    "Scm_OpenKeyForService(lpServiceName, FALSE);",
    "Scm_QueryServiceByName(lpServiceName, FALSE, FALSE);",
    "name = Dll_Alloc(",
    "if (! name) {",
    "SetLastError(ERROR_NOT_ENOUGH_MEMORY);",
    "*(ULONG *)name = tzuk;",
    "wcscpy((WCHAR *)(((ULONG *)name) + 1), lpServiceName);",
    "_wcslwr((WCHAR *)(((ULONG *)name) + 1));",
]:
    require(open_impl, term, "OpenServiceWImpl topology")

reject(open_impl, "_wcslwr(name);", "marker-inclusive lower-case")

alloc_start = source.index("_FX WCHAR *Scm_AllocServiceKeyPath(")
alloc_end = source.index("// Scm_OpenKeyForService", alloc_start)
alloc_path = source[alloc_start:alloc_end]

for term in [
    "if ((! ServiceName) || (! *ServiceName))",
    "SetLastError(ERROR_INVALID_PARAMETER);",
    "service_len = wcslen(ServiceName);",
    "if (service_len > SCM_SERVICE_NAME_MAX_CHARS)",
    "SetLastError(ERROR_INVALID_NAME);",
    "key_len = wcslen(Scm_ServicesKeyPath) + 1 + service_len + 1;",
    "Dll_AllocTemp((ULONG)(key_len * sizeof(WCHAR)))",
    "SetLastError(ERROR_NOT_ENOUGH_MEMORY);",
    "wcscpy(keyname, Scm_ServicesKeyPath);",
    "wcscat(keyname, L\"\\\\\");",
    "wcscat(keyname, ServiceName);",
]:
    require(alloc_path, term, "Scm_AllocServiceKeyPath")

open_key_start = source.index("_FX HANDLE Scm_OpenKeyForService(")
open_key_end = source.index("// SbieDll_IsBoxedService", open_key_start)
open_key = source[open_key_start:open_key_end]

for term in [
    "WCHAR *keyname;",
    "keyname = Scm_AllocServiceKeyPath(ServiceName);",
    "if (! keyname)",
    "RtlInitUnicodeString(&objname, keyname);",
    "InitializeObjectAttributes(",
    "NtCreateKey(",
    "NtOpenKey(&handle, KEY_QUERY_VALUE, &objattrs);",
    "SetLastError(error);",
    "Dll_Free(keyname);",
    "return handle;",
]:
    require(open_key, term, "Scm_OpenKeyForService")

reject(open_key, "WCHAR keyname[128];", "old fixed stack service key buffer")
reject(open_key, "wcscpy(keyname, Scm_ServicesKeyPath);\n    wcscat(keyname, L\"\\\\\");\n    wcscat(keyname, ServiceName);", "old inline stack path construction")

discard_start = source.index("_FX void Scm_DiscardKeyCache(")
discard_end = source.index("// SbieDll_CheckProcessLocalSystem", discard_start)
discard = source[discard_start:discard_end]

for term in [
    "ULONG error = GetLastError();",
    "Dll_AllocTemp(",
    "Key_UpdateMergeByPath(keyname, FALSE, FALSE);",
    "keyname = Scm_AllocServiceKeyPath(ServiceName);",
    "if (keyname) {",
    "Dll_Free(keyname);",
    "SetLastError(error);",
]:
    require(discard, term, "Scm_DiscardKeyCache")

reject(discard, "Dll_AllocTemp(sizeof(WCHAR) * 256)", "old fixed discard key buffer")

for term in [
    "### SREV-114: SCM Service Key Path Shape",
    "SCM_SERVICE_KEY_PATH_SHAPE",
    "srev-114-scm-service-key-path-shape.schema.json",
    "Sandboxie/core/dll/scm.c",
    "Scm_AllocServiceKeyPath",
    "Scm_OpenKeyForService",
    "Scm_DiscardKeyCache",
    "SCM_SERVICE_NAME_MAX_CHARS",
]:
    require(ledger, term, "ledger")

print("SREV-114 schema/source gate passed")
