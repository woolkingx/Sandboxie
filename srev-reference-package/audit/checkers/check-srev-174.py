#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-174 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-174 failed: stale {label} still present")


def section(text: str, start: str, end: str) -> str:
    start_index = text.index(start)
    end_index = text.index(end, start_index)
    return text[start_index:end_index]


schema = json.loads((ROOT / "docs/plan/srev-174-dllpath-pool-lifetime.schema.json").read_text())
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-174 failed: schema is not draft-07")
if schema.get("id") != "DLLPATH_POOL_LIFETIME":
    raise SystemExit("SREV-174 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "dllpath.c owns the DLL-side path list cache and its pool/list lifetime",
    "pool2 owns refreshable file path PATTERN nodes",
    "file path refresh must build a complete replacement in a new pool before publishing it",
    "refresh failure must preserve the last successfully published file path lists and their pool",
    "old pool2 may be deleted only after the replacement pool and list heads are published",
    "partially built replacement lists are discarded by deleting the replacement pool",
    "Dll_InitPathList must delete earlier pools when later initialization steps fail",
    "SREV-174 does not change path code selection pattern matching semantics driver refresh ownership lock ownership or the path list wire format",
    "Linux source gate is not Windows refresh runtime proof",
]:
    require(contracts, term, "schema")

dllpath_c = (ROOT / "Sandboxie/core/dll/dllpath.c").read_text()
sbieapi_c = (ROOT / "Sandboxie/core/dll/sbieapi.c").read_text()
process_api_c = (ROOT / "Sandboxie/core/drv/process_api.c").read_text()
file_c = (ROOT / "Sandboxie/core/drv/file.c").read_text()
pool_c = (ROOT / "Sandboxie/common/pool.c").read_text()
spec = (ROOT / "docs/plan/srev-174-dllpath-pool-lifetime.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-174.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "_FX LONG SbieApi_QueryPathList(",
    "args->path_code.val = path_code;",
    "args->prepend_level.val = prepend_level;",
]:
    require(sbieapi_c, term, "sbieapi.c path-list API wrapper")

for term in [
    "_FX NTSTATUS Process_Api_QueryPathList(",
    "if (prepend_level) path_len += sizeof(ULONG);",
    "*((ULONG*)path) = Pattern_Level(pat);",
    "*((ULONG*)path) = -1;",
]:
    require(process_api_c, term, "driver path-list wire producer")

for term in [
    "_FX NTSTATUS File_Api_RefreshPathList(",
    "ok = File_InitPaths(proc,",
    "if (ok) {",
    "File_PurgePathList(&proc->open_file_paths);",
]:
    require(file_c, term, "driver refresh owner surface")

for term in [
    "ALIGNED POOL *Pool_Create(void)",
    "ALIGNED ULONG Pool_Delete(POOL *pool)",
    "Pool_Free_Mem(page, page->eyecatcher);",
]:
    require(pool_c, term, "pool lifetime primitives")

init = section(dllpath_c, "_FX BOOLEAN Dll_InitPathList(void)", "// Dll_InitPathList2")
for term in [
    "pool = Pool_Create();",
    "pool2 = Pool_Create();",
    "Pool_Delete(pool);\n        return FALSE;",
    "Pool_Delete(pool2);\n        Pool_Delete(pool);\n        return FALSE;",
    "anchor->pool = pool;",
    "anchor->pool2 = pool2;",
]:
    require(init, term, "Dll_InitPathList cleanup")

refresh = section(dllpath_c, "_FX void Dll_RefreshPathList(void)", "// SbieDll_IsParentReadable")
for term in [
    "EnterCriticalSection(&Dll_FilePathListCritSec);",
    "if (SbieApi_Call(API_REFRESH_FILE_PATH_LIST, 0) == STATUS_SUCCESS) {",
    "POOL *pool2 = Pool_Create();",
    "if (pool2) {",
    "if (Dll_InitPathList2(pool2, 'fx', &normal_paths, &open_paths, &closed_paths, &write_paths, &read_paths)) {",
    "POOL *old_pool2 = Dll_PathListAnchor->pool2;",
    "Dll_PathListAnchor->pool2 = pool2;",
    "memcpy(&Dll_PathListAnchor->open_file_path,     &open_paths, sizeof(LIST));",
    "Dll_PathListAnchor->file_paths_initialized = TRUE;",
    "Pool_Delete(old_pool2);",
    "pool2 = NULL;",
    "if (pool2)\n                Pool_Delete(pool2);",
    "LeaveCriticalSection(&Dll_FilePathListCritSec);",
]:
    require(refresh, term, "Dll_RefreshPathList two-phase publish")

reject(
    refresh,
    "Pool_Delete(Dll_PathListAnchor->pool2);\n            Dll_PathListAnchor->pool2 = pool2;",
    "pre-build old pool deletion",
)
reject(
    refresh,
    "Dll_InitPathList2(Dll_PathListAnchor->pool2, 'fx'",
    "rebuild into already published pool",
)

for term in [
    "### SREV-174: DLL Path List Pool Lifetime",
    "DLLPATH_POOL_LIFETIME",
    "srev-174-dllpath-pool-lifetime.schema.json",
    "Sandboxie/core/dll/dllpath.c",
    "Dll_RefreshPathList",
    "pool2",
    "last successfully published file path lists",
    "Windows DLL build",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-174 schema/source gate passed")
