# SREV-197: WMP Shell COM Input Contract

Stage: schema -> boundary -> action -> verify

Input artifact: `Sandboxie/core/svc/comserver9_wmp.c`

Output artifact: the WMP/WinAmp/KMPlayer Shell COM shim copies parameter and
selection strings as owned strings, releases Shell-allocated memory through the
documented owner API, and releases drag/drop `STGMEDIUM` through
`ReleaseStgMedium`.

Owner: `Sandboxie/core/svc/comserver9_wmp.c`

Build projection: `Sandboxie/core/svc/SboxSvc.vcxproj`

Acceptance gate: `docs/plan/check-srev-197.py` plus
`docs/plan/check-srev-197.sh`.

## Data

`comserver9_wmp.c` synthesizes `IExecuteCommand`,
`IObjectWithSelection`, and `IDropTarget` implementations. The important data
crossings are:

- `IExecuteCommand::SetParameters` passes an input `LPCWSTR` command parameter
  string into Sandboxie's restart command path.
- `IObjectWithSelection::SetSelection` passes `IShellItemArray` items and
  `IShellItem::GetDisplayName(SIGDN_FILESYSPATH)` output strings into the same
  parameter accumulator.
- `IDataObject::GetData(CF_HDROP/TYMED_HGLOBAL)` passes drag/drop data through
  `STGMEDIUM` into the drop handler.

Local evidence:

- `SetParameters` allocated a buffer and then called `wmemcmp` instead of a copy
  routine, leaving `WMPServer_Parameters` uninitialized except for the final
  terminator.
- Leading-space trimming advanced the global pointer, so the allocation base was
  no longer owned by `WMPServer_Parameters`.
- `SetSelection` appended Shell item paths with unchecked `ULONG` byte math,
  `wcscpy`/`wcscat`, and did not release the `GetDisplayName` string with
  `CoTaskMemFree`.
- `Drop` manually inspected the `HGLOBAL` and manually released pieces of
  `STGMEDIUM` instead of using the documented data-transfer release owner.

## Official API Shape

`IExecuteCommand::SetParameters` provides a string pointer whose format and
contents belong to the invoked verb:

https://learn.microsoft.com/en-us/windows/win32/api/shobjidl_core/nf-shobjidl_core-iexecutecommand-setparameters

`IObjectWithSelection::SetSelection` receives an `IShellItemArray`:

https://learn.microsoft.com/en-us/windows/win32/api/shobjidl_core/nf-shobjidl_core-iobjectwithselection-setselection

`IShellItemArray::GetItemAt` returns an `IShellItem *` for a given index:

https://learn.microsoft.com/en-us/windows/win32/api/shobjidl_core/nf-shobjidl_core-ishellitemarray-getitemat

`IShellItem::GetDisplayName` returns an allocated string that the caller must
release with `CoTaskMemFree`:

https://learn.microsoft.com/en-us/windows/win32/api/shobjidl_core/nf-shobjidl_core-ishellitem-getdisplayname

`IDataObject::GetData` transfers data through `STGMEDIUM` and the caller
assumes responsibility for releasing it:

https://learn.microsoft.com/en-us/windows/win32/api/objidl/nf-objidl-idataobject-getdata

`ReleaseStgMedium` is the documented release owner for storage medium structures
used by `IDataObject::GetData`:

https://learn.microsoft.com/en-us/windows/win32/api/ole2/nf-ole2-releasestgmedium

For `CF_HDROP`, Microsoft Shell documentation says to use `DragQueryFile` to
extract file names from the global memory object:

https://learn.microsoft.com/en-us/windows/win32/shell/clipboard
https://learn.microsoft.com/en-us/windows/win32/api/shellapi/nf-shellapi-dragqueryfilea

## Boundary

The boundary is:

```text
Shell COM caller -> comserver9_wmp.c shim -> ComServer_RestartProgram
```

`comserver9_wmp.c` owns turning Shell-owned strings and storage mediums into a
local command argument string. Shell-owned allocations must be released through
the Shell/COM owner API, not by leaking or by manual partial release.

## Topology

```text
SetParameters
  -> trim only while preserving allocation base
  -> checked WCHAR byte count
  -> wmemcpy into owned WMPServer_Parameters

SetSelection
  -> IShellItemArray::GetItemAt
  -> IShellItem::GetDisplayName(SIGDN_FILESYSPATH)
  -> append quoted path with checked WCHAR byte count
  -> CoTaskMemFree(path)

Drop
  -> IDataObject::GetData(CF_HDROP/TYMED_HGLOBAL)
  -> DragQueryFile
  -> ComServer_RestartProgram
  -> ReleaseStgMedium
```

## Logic

The shim is not allowed to treat Shell input buffers as if they were local,
unbounded, or permanently owned by Sandboxie. The fix is to:

- replace the non-copying `wmemcmp` call with an owned `wmemcpy` copy;
- keep `WMPServer_Parameters` pointing at its allocation base;
- guard WCHAR byte-count conversion before `Dll_Alloc`;
- append selected paths through a bounded builder instead of `wcscpy`/`wcscat`;
- release `IShellItem::GetDisplayName` output with `CoTaskMemFree`;
- use `DragQueryFile` for `CF_HDROP` and `ReleaseStgMedium` for the returned
  `STGMEDIUM`;
- guard pointer output parameters before writing through them.

## Verification

Linux source gates prove:

- no stale `wmemcmp`, `wcscpy`, `wcscat`, `GlobalLock`, `GlobalUnlock`,
  `GlobalFree`, or manual `pUnkForRelease` release remains in the WMP shim;
- parameter and selection construction uses checked byte counts and owned
  `wmemcpy`;
- `CoTaskMemFree` and `ReleaseStgMedium` are present on the documented owner
  boundaries;
- drop handling uses `DragQueryFile` for `CF_HDROP`.
- `SboxSvc.vcxproj` links `Shell32.lib` for every service configuration so the
  `DragQueryFileW` import used by the WMP drop handler resolves at link time.

Runtime gate:

- Windows SbieSvc COM-server build.
- WMP play/enqueue verb smoke with direct parameters, multiple selected files,
  empty parameters, leading spaces, drag/drop CF_HDROP, and malformed/null COM
  pointer arguments.
