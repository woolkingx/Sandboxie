# SREV-158: Ole HGLOBAL Lock And CIDA Copy Gates

## Stage Gate

```text
stage: schema -> boundary -> topology -> logic -> action -> verify
input artifact: Sandboxie/core/dll/ole.cpp
output artifact: checked HGLOBAL lock/copy gates and corrected CIDA child PIDL copy
owner: Sandboxie/core/dll/ole.cpp
acceptance gate: docs/plan/check-srev-158.py and docs/plan/check-srev-158.sh
```

## Data

`Sandboxie/core/dll/ole.cpp` wraps OLE clipboard and drag/drop data objects.
`XDataObject::GetData`, `InitFormatHDrop`, `InitFormatFileNameA`,
`InitFormatFileNameW`, and `InitFormatIdList` synthesize or rewrite
`TYMED_HGLOBAL` storage for `CF_HDROP`, `CFSTR_FILENAMEA`,
`CFSTR_FILENAMEW`, and `CFSTR_SHELLIDLIST`.

Before this SREV, several active paths locked movable `HGLOBAL` handles and
immediately dereferenced the returned pointer. If `GlobalLock` failed, the
code could dereference `NULL` or return a partially initialized medium. The
Shell ID List rewrite path also computed each child PIDL size with
`GetPidl(count)` but copied bytes from the parent folder PIDL variable, so the
new `CIDA` offsets did not point at the corresponding child item data.

## Official Shape

- Microsoft documents `GlobalAlloc` as returning a handle or `NULL` on failure:
  `https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-globalalloc`.
- Microsoft documents `GlobalLock` as locking a global memory object and
  returning a pointer to the first byte, or `NULL` on failure:
  `https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-globallock`.
- Microsoft documents `GlobalUnlock` as decrementing the lock count of a global
  memory object:
  `https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-globalunlock`.
- Microsoft documents `STGMEDIUM` as the data-transfer medium used by
  `IDataObject` and names `hGlobal` for `TYMED_HGLOBAL`:
  `https://learn.microsoft.com/en-us/windows/win32/api/objidl/ns-objidl-stgmedium-r1`.
- Microsoft documents `IDataObject::GetData` as returning data in the
  specified `STGMEDIUM` and returning `STG_E_MEDIUMFULL` when the medium cannot
  be allocated:
  `https://learn.microsoft.com/en-us/windows/win32/api/objidl/nf-objidl-idataobject-getdata`.
- Microsoft documents Shell clipboard format `CFSTR_SHELLIDLIST` as a `CIDA`
  structure whose `aoffset` array contains the offset of the parent folder PIDL
  followed by offsets for each selected child PIDL:
  `https://learn.microsoft.com/en-us/windows/win32/shell/clipboard`.

## Schema

`OLE_HGLOBAL_LOCK_AND_CIDA_COPY_GATES` says:

- every active `GlobalLock` result dereferenced by `ole.cpp` must be non-null
  before copy or API use;
- every successful active `GlobalLock` in these copy paths must be followed by
  `GlobalUnlock` before the function returns through the local path;
- failed output `HGLOBAL` locks free the newly allocated handle before returning
  failure or `NULL`;
- `XDataObject::GetData` does not publish a caller-visible `STGMEDIUM` unless
  both source and destination `HGLOBAL` locks succeed;
- `CFSTR_SHELLIDLIST` rewrite keeps `CIDA` offset topology: offset zero copies
  the rewritten parent PIDL and child offsets copy `GetPidl(count)`;
- this SREV does not change the supported clipboard formats, sandbox path
  translation policy, drag/drop scheduling, or the inactive virtual-file
  extraction experiment.

## Topology

Legal `TYMED_HGLOBAL` rewrite flow:

```text
incoming HGLOBAL or HDROP
-> GlobalSize / format-specific size calculation
-> GlobalAlloc(GMEM_MOVEABLE, size)
-> GlobalLock source and/or destination
-> copy only after every required lock succeeds
-> GlobalUnlock every successful lock
-> publish STGMEDIUM or return replacement HGLOBAL
```

Legal `CFSTR_SHELLIDLIST` rewrite flow:

```text
original CIDA
-> parent PIDL plus child PIDL offsets
-> translated sandbox parent path
-> SHILCreateFromPath translated parent PIDL
-> new CIDA offset 0 copies translated parent PIDL
-> new CIDA child offsets copy the matching original GetPidl(count)
```

## Logic Risk

OLE clipboard and drag/drop consumers treat `STGMEDIUM` ownership and `CIDA`
offsets as data contracts. Publishing a medium after a failed lock can crash the
caller or leak a partially initialized handle. Rebuilding a CIDA array with
child offsets that point at parent PIDL bytes breaks the Shell ID List shape and
can make a receiver resolve the wrong object. The correct local repair is to
gate every local lock-before-copy edge and preserve the parent/child PIDL
topology.

## Fix

`XDataObject::GetData` now fails with `STG_E_MEDIUMFULL` and frees the newly
allocated `HGLOBAL` if either source or destination lock fails. The HDROP,
filename, and ID-list rewrite helpers now free their own output `HGLOBAL` and
return `NULL` if an output lock fails; filename input locks now return `NULL`
before `CreateFileA/W` if the incoming medium cannot be locked. The ID-list
rewrite now copies `GetPidl(count)` for child entries instead of copying the
parent PIDL bytes with the child size.

## Verification

Source-level gates:

```bash
python3 docs/plan/check-srev-158.py
bash docs/plan/check-srev-158.sh
python3 docs/plan/check-core-coverage.py
```

Full closure matrix:

```bash
python3 docs/plan/check-srev-158.py &&
bash docs/plan/check-srev-158.sh &&
python3 docs/plan/check-core-coverage.py &&
for s in docs/plan/check-srev-0*.sh docs/plan/check-srev-1*.sh docs/plan/check-kpath-0*.sh; do bash "$s"; done &&
git diff --check
```

Runtime/build gate: Windows DLL build; clipboard and drag/drop smoke for
`CF_HDROP`, `CFSTR_FILENAMEA`, `CFSTR_FILENAMEW`, and `CFSTR_SHELLIDLIST`;
fault-injection or debugger-assisted `GlobalLock` failure proving no null
dereference and no leaked replacement `HGLOBAL`; Shell ID List drop/paste smoke
proving parent folder and child item PIDLs still resolve correctly.
