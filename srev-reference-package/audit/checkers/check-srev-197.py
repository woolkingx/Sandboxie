#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-197 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-197 failed: stale {label} remains {needle!r}")


def between(text: str, start: str, end: str) -> str:
    a = text.index(start)
    b = text.index(end, a + len(start))
    return text[a:b]


schema = json.loads(
    (ROOT / "docs/plan/srev-197-wmp-shell-com-input-contract.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-197 failed: schema is not draft-07")
if schema.get("id") != "WMP_SHELL_COM_INPUT_CONTRACT":
    raise SystemExit("SREV-197 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/svc/comserver9_wmp.c":
    raise SystemExit("SREV-197 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "SetParameters copies parameter text; comparison routines are not legal copies",
    "WMPServer_Parameters always points at the allocation base or is NULL",
    "WCHAR byte counts are checked before Dll_Alloc",
    "SetSelection validates psia before dereference",
    "IShellItem::GetDisplayName output is released with CoTaskMemFree",
    "Selection append uses bounded wmemcpy builder instead of wcscpy/wcscat",
    "IDropTarget effect output pointers are checked before write",
    "IDataObject::GetData STGMEDIUM is released with ReleaseStgMedium",
    "CF_HDROP extraction uses DragQueryFile instead of direct DROPFILES pointer walking",
    "SboxSvc.vcxproj links Shell32.lib",
]:
    require(contracts, term, "schema contract")

src = (ROOT / "Sandboxie/core/svc/comserver9_wmp.c").read_text()
svc_project = (ROOT / "Sandboxie/core/svc/SboxSvc.vcxproj").read_text()
spec = (ROOT / "docs/plan/srev-197-wmp-shell-com-input-contract.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-197.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "#include <shobjidl.h>",
    "#include <shlobj.h>",
    "#include <shellapi.h>",
    "static BOOLEAN WMPServer_TryWcharBytes(SIZE_T chars, ULONG *bytes);",
    "static void WMPServer_ClearParameters(void);",
    "static HRESULT WMPServer_SetParametersCopy(LPCWSTR pszParameters);",
    "static HRESULT WMPServer_AppendParameterPath(LPCWSTR path);",
]:
    require(src, term, "declarations")

if svc_project.count("Shell32.lib") != 8:
    raise SystemExit("SREV-197 failed: SboxSvc.vcxproj must link Shell32.lib in every service configuration")

reject(src, "wmemcmp(", "non-copying parameter compare")
reject(src, "wcscpy(", "unbounded string copy")
reject(src, "wcscat(", "unbounded string append")
reject(src, "GlobalLock(", "direct HGLOBAL lock")
reject(src, "GlobalUnlock(", "direct HGLOBAL unlock")
reject(src, "GlobalFree(", "manual STGMEDIUM hGlobal release")
reject(src, "pUnkForRelease", "manual STGMEDIUM provider release")

bytes_helper = between(
    src,
    "_FX BOOLEAN WMPServer_TryWcharBytes(",
    "//---------------------------------------------------------------------------\n// WMPServer_ClearParameters",
)
for term in [
    "if (chars > ((ULONG)-1) / sizeof(WCHAR))",
    "*bytes = (ULONG)(chars * sizeof(WCHAR));",
    "return TRUE;",
]:
    require(bytes_helper, term, "checked WCHAR byte helper")

clear = between(
    src,
    "_FX void WMPServer_ClearParameters(",
    "//---------------------------------------------------------------------------\n// WMPServer_SetParametersCopy",
)
for term in [
    "if (WMPServer_Parameters)",
    "HeapFree(GetProcessHeap(), 0, WMPServer_Parameters);",
    "WMPServer_Parameters = NULL;",
]:
    require(clear, term, "parameter ownership clear")

copy = between(
    src,
    "_FX HRESULT WMPServer_SetParametersCopy(",
    "//---------------------------------------------------------------------------\n// WMPServer_AppendParameterPath",
)
for term in [
    "WMPServer_ClearParameters();",
    "if (! pszParameters)",
    "len = wcslen(pszParameters);",
    "while (trim < len && pszParameters[trim] == L' ')",
    "if (! WMPServer_TryWcharBytes(len + 1, &bytes))",
    "params = Dll_Alloc(bytes);",
    "wmemcpy(params, pszParameters + trim, len);",
    "params[len] = L'\\0';",
    "WMPServer_Parameters = params;",
]:
    require(copy, term, "SetParameters owned copy")
if not copy.index("wmemcpy(params, pszParameters + trim, len);") < copy.index("WMPServer_Parameters = params;"):
    raise SystemExit("SREV-197 failed: parameters published before copy")

append = between(
    src,
    "_FX HRESULT WMPServer_AppendParameterPath(",
    "//---------------------------------------------------------------------------\n// WMPServer_MyCreateInstance",
)
for term in [
    "param_len = WMPServer_Parameters ? wcslen(WMPServer_Parameters) : 0;",
    "path_len = wcslen(path);",
    "chars = param_len + path_len + 4;",
    "if (chars < param_len || chars < path_len)",
    "WMPServer_TryWcharBytes(chars, &bytes)",
    "params = Dll_Alloc(bytes);",
    "wmemcpy(ptr, WMPServer_Parameters, param_len);",
    "wmemcpy(ptr, path, path_len);",
    "WMPServer_ClearParameters();",
    "WMPServer_Parameters = params;",
]:
    require(append, term, "selection bounded append")
if not append.index("wmemcpy(ptr, path, path_len);") < append.index("WMPServer_Parameters = params;"):
    raise SystemExit("SREV-197 failed: selection parameters published before path copy")

set_params = between(
    src,
    "_FX HRESULT WMPServer_IExecuteCommand_SetParameters(",
    "//---------------------------------------------------------------------------\n// WMPServer_IExecuteCommand_SetPosition",
)
for term in [
    "HRESULT hr = WMPServer_SetParametersCopy(pszParameters);",
    "if (FAILED(hr))",
    "return hr;",
]:
    require(set_params, term, "SetParameters wrapper")

set_directory = between(
    src,
    "_FX HRESULT WMPServer_IExecuteCommand_SetDirectory(",
    "//---------------------------------------------------------------------------\n// WMPServer_IExecuteCommand_Execute",
)
for term in [
    "if (pszDirectory)",
    "SetCurrentDirectory(pszDirectory);",
]:
    require(set_directory, term, "SetDirectory null gate")

selection = between(
    src,
    "_FX HRESULT WMPServer_IObjectWithSelection_SetSelection(",
    "//---------------------------------------------------------------------------\n// WMPServer_IObjectWithSelection_GetSelection",
)
for term in [
    "if (! psia)",
    "return E_POINTER;",
    "psia->lpVtbl->GetItemAt(psia, index, &pShellItem);",
    "IShellItem_GetDisplayName(pShellItem, SIGDN_FILESYSPATH, &path1);",
    "WMPServer_AppendParameterPath(path1);",
    "CoTaskMemFree(path1);",
    "IShellItem_Release(pShellItem);",
]:
    require(selection, term, "SetSelection shell ownership")
if not selection.index("CoTaskMemFree(path1);") < selection.index("IShellItem_Release(pShellItem);"):
    raise SystemExit("SREV-197 failed: path string is not freed before item release")

drag_enter = between(
    src,
    "_FX HRESULT WMPServer_IDropTarget_DragEnter(",
    "//---------------------------------------------------------------------------\n// WMPServer_IDropTarget_DragOver",
)
require(drag_enter, "if (! pdwEffect)", "DragEnter output pointer gate")

drag_over = between(
    src,
    "_FX HRESULT WMPServer_IDropTarget_DragOver(",
    "//---------------------------------------------------------------------------\n// WMPServer_IDropTarget_DragLeave",
)
require(drag_over, "if (! pdwEffect)", "DragOver output pointer gate")

drop = between(
    src,
    "_FX HRESULT WMPServer_IDropTarget_Drop(",
    "\n}",
)
for term in [
    "if ((! pDataObject) || (! pdwEffect))",
    "IDataObject_GetData(pDataObject, &format, &medium);",
    "medium.tymed == TYMED_HGLOBAL && medium.hGlobal",
    "DragQueryFile(hDrop, 0xFFFFFFFF, NULL, 0);",
    "DragQueryFile(hDrop, 0, NULL, 0);",
    "WMPServer_TryWcharBytes((SIZE_T)chars + 1, &bytes)",
    "DragQueryFile(hDrop, 0, path, chars + 1)",
    "ComServer_RestartProgram(path);",
    "ReleaseStgMedium(&medium);",
]:
    require(drop, term, "Drop STGMEDIUM/CF_HDROP gate")

for term in [
    "kind: srev-ledger-entry",
    "id: SREV-197",
    "owner: Sandboxie/core/svc/comserver9_wmp.c",
    "spec: docs/plan/srev-197-wmp-shell-com-input-contract.md",
    "schema: docs/plan/srev-197-wmp-shell-com-input-contract.schema.json",
    "checker: docs/plan/check-srev-197.py",
    "| Status | patched source-level after official Shell COM shape review; needs Windows runtime proof |",
]:
    require(ledger_fragment, term, "ledger fragment")

for term in [
    "### SREV-197: WMP Shell COM Input Contract",
    "WMP_SHELL_COM_INPUT_CONTRACT",
    "Sandboxie/core/svc/comserver9_wmp.c",
    "WMPServer_SetParametersCopy",
    "CoTaskMemFree",
    "DragQueryFile",
    "ReleaseStgMedium",
]:
    require(ledger, term, "combined ledger")
require(ledger_fragment, "SboxSvc.vcxproj", "ledger fragment")

print("SREV-197 schema/source gate passed")
