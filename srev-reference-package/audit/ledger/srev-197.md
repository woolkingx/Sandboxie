---
kind: srev-ledger-entry
id: SREV-197
title: WMP Shell COM Input Contract
status: patched-source-level-after-official-shell-com-shape-review-needs-windows-runtime-proof
owner: Sandboxie/core/svc/comserver9_wmp.c
spec: docs/plan/srev-197-wmp-shell-com-input-contract.md
schema: docs/plan/srev-197-wmp-shell-com-input-contract.schema.json
checker: docs/plan/check-srev-197.py
runtime_gate: Windows SbieSvc COM-server build plus WMP play/enqueue, selection, and CF_HDROP smoke
---
### SREV-197: WMP Shell COM Input Contract

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official Shell COM shape review; needs Windows runtime proof |
| Evidence | `Sandboxie/core/svc/comserver9_wmp.c` was the top unnamed reviewable core file after SREV-196. It synthesizes `IExecuteCommand`, `IObjectWithSelection`, and `IDropTarget` for WMP/WinAmp/KMPlayer restart routing. Before this fix, `SetParameters` allocated a buffer but called `wmemcmp` instead of copying the input string, leading-space trimming advanced the global parameter pointer away from the allocation base, `SetSelection` did unchecked string concatenation and leaked `IShellItem::GetDisplayName` output, and `Drop` manually released `STGMEDIUM` pieces instead of using the documented release owner. |
| Data | `IExecuteCommand::SetParameters`, `IObjectWithSelection::SetSelection`, `IShellItemArray::GetItemAt`, `IShellItem::GetDisplayName`, `CoTaskMemFree`, `IDataObject::GetData`, `STGMEDIUM`, `CF_HDROP`, `DragQueryFile`, `ReleaseStgMedium`, `WMPServer_Parameters`, and `SboxSvc.vcxproj` Shell32 link dependency. |
| Schema | `WMP_SHELL_COM_INPUT_CONTRACT` says Shell-provided strings must be copied into owned storage, WCHAR byte counts must be checked before allocation, `GetDisplayName` output must be freed with `CoTaskMemFree`, `IDataObject::GetData` storage must be released with `ReleaseStgMedium`, and CF_HDROP file names must be extracted through `DragQueryFile` instead of direct `DROPFILES` pointer walking. |
| Topology | Legal flow is `Shell COM caller -> WMP shim -> owned WMPServer_Parameters or temporary drop path -> ComServer_RestartProgram`, with Shell allocation ownership returned at each boundary. |
| Logic Risk | The old `wmemcmp` left `WMPServer_Parameters` uninitialized. The old append path could overflow `ULONG` byte math, leak Shell strings, and build command arguments through unbounded concatenation. The old drop path could skip the provider-selected `STGMEDIUM` release semantics and dereference malformed or unexpected storage. |
| Official Shape | `docs/plan/srev-197-wmp-shell-com-input-contract.md` records Microsoft `IExecuteCommand`, `IObjectWithSelection`, `IShellItemArray`, `IShellItem::GetDisplayName`, `IDataObject::GetData`, `ReleaseStgMedium`, Shell clipboard, and `DragQueryFile` references. `docs/plan/srev-197-wmp-shell-com-input-contract.schema.json` records the JSON Schema draft-07 local `WMP_SHELL_COM_INPUT_CONTRACT` contract. |
| Fix | `comserver9_wmp.c` now owns parameter copying through `WMPServer_SetParametersCopy`, bounds WCHAR byte counts with `WMPServer_TryWcharBytes`, keeps `WMPServer_Parameters` at the allocation base, appends selection paths through `WMPServer_AppendParameterPath`, releases `GetDisplayName` output with `CoTaskMemFree`, guards pointer outputs, extracts CF_HDROP with `DragQueryFile`, and releases the returned medium with `ReleaseStgMedium`. `SboxSvc.vcxproj` links `Shell32.lib` in every service configuration so the `DragQueryFileW` import resolves. |
| Acceptance Gate | `docs/plan/check-srev-197.py` validates the draft-07 schema, official references, Shell COM helper topology, stale non-copy/manual-release removal, bounded parameter and selection builders, `CoTaskMemFree`, `DragQueryFile`, `ReleaseStgMedium`, pointer gates, `SboxSvc.vcxproj` Shell32 link coverage, and split ledger fragment; `docs/plan/check-srev-197.sh` is the targeted wrapper. Runtime gate: Windows SbieSvc COM-server build plus WMP play/enqueue, direct parameter, multiple selection, empty/leading-space parameter, CF_HDROP, and malformed/null pointer smoke. |
