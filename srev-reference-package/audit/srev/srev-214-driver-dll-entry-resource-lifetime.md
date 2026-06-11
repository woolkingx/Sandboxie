# SREV-214: Driver DLL Entry Resource Lifetime

## Stage

schema -> boundary -> topology -> logic -> action -> verify

## Evidence

`Sandboxie/core/drv/dll.c` was the top unnamed reviewable core file after
SREV-213. It owns driver-side DLL image loading for syscall/export discovery.
`Dll_Load` allocates a `DLL_ENTRY`, opens a system DLL with `ZwCreateFile`,
creates a section with `ZwCreateSection`, maps it with `ZwMapViewOfSection`,
parses the PE export directory, and stores the resulting entry in `Dll_List`.

Before this fix, `Dll_Load` treated initialization failure by logging and
returning `NULL`, but it did not unwind resources already acquired on that
path. A failure after file open, section creation, or view mapping could leave
the file handle, section handle, mapped view, and `DLL_ENTRY` allocation alive.
`Dll_Unload` released the map and handles for successful entries, but did not
free the `DLL_ENTRY` allocation itself. The file open also used only
`OBJ_CASE_INSENSITIVE` even though the handle is driver-private.

## Data

`dll.c`, `dll.h`, `Dll_Load`, `Dll_Unload`, `DLL_ENTRY`, `Dll_List`,
`Driver_Pool`, `Mem_Alloc`, `Mem_Free`, `InitializeObjectAttributes`,
`OBJ_CASE_INSENSITIVE`, `OBJ_KERNEL_HANDLE`, `ZwCreateFile`,
`ZwQueryInformationFile`, `ZwCreateSection`, `ZwMapViewOfSection`,
`ZwUnmapViewOfSection`, `ZwClose`, `Dll_RvaToAddr`, `Dll_GetProc`,
`Syscall_Init_List`, `Syscall_Init_ServiceData`, `Syscall_Init32`, and
`Driver_FindMissingServices`.

## Official Shape

Microsoft documents `ZwCreateFile` as returning a file handle through
`FileHandle`; when that handle is no longer used, the driver must call
`ZwClose`. The same page says a caller that is not running in a system thread
context must use `OBJ_KERNEL_HANDLE`, and must ensure created handles are
private if it is not running in system thread context.

Microsoft documents `ZwCreateSection` as returning a section handle and says
the driver must call `ZwClose` when that handle is no longer used. It also
states that private handles must use the same `OBJ_KERNEL_HANDLE` rule when the
caller is not running in a system thread context.

Microsoft documents `ZwMapViewOfSection` as mapping a section view, and
`ZwUnmapViewOfSection` as the operation that unmaps the entire view containing
the base address. The object-handle guidance says private driver handles must
specify `OBJ_KERNEL_HANDLE` so user-mode applications cannot access them.

References:

- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-zwcreatefile`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-zwcreatesection`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-zwmapviewofsection`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-zwunmapviewofsection`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-zwclose`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/kernel/object-handles`

## Schema

`DRIVER_DLL_ENTRY_RESOURCE_LIFETIME` says:

- `dll.c` owns driver-side DLL image load entries.
- A `DLL_ENTRY` owns exactly one optional mapped view, one optional section
  handle, one optional file handle, and its pool allocation.
- Failure after any partial acquisition must release the acquired view, section
  handle, file handle, and pool allocation before returning `NULL`.
- Successful entries remain owned by `Dll_List` until `Dll_Unload` removes and
  releases them.
- Driver-private handles opened by this loader must use
  `OBJ_CASE_INSENSITIVE | OBJ_KERNEL_HANDLE`.

## Topology

Load topology:

```text
Dll_Load
-> Mem_Alloc(DLL_ENTRY)
-> InitializeObjectAttributes(OBJ_CASE_INSENSITIVE | OBJ_KERNEL_HANDLE)
-> ZwCreateFile(file handle)
-> ZwQueryInformationFile(file size)
-> ZwCreateSection(section handle backed by file handle)
-> ZwMapViewOfSection(view in current process)
-> PE export parse
-> List_Insert_After(Dll_List)
```

Failure topology:

```text
partial DLL_ENTRY
-> optional ZwUnmapViewOfSection(mapped view)
-> optional ZwClose(section handle)
-> optional ZwClose(file handle)
-> Mem_Free(DLL_ENTRY)
-> return NULL
```

Unload topology:

```text
Dll_Unload
-> List_Remove(Dll_List entry)
-> same DLL_ENTRY release helper
```

## Logic Risk

The local owner of a `DLL_ENTRY` is ambiguous unless acquisition and release
are paired in one place. Returning `NULL` after logging hides the failed entry
from `Dll_List`, so later unload cannot find it. Successful entries have the
inverse leak: unload removes them from the list and releases OS resources but
does not release the pool allocation. The missing `OBJ_KERNEL_HANDLE` is a
separate boundary error: the DLL file handle is driver-private, not a handle
intended for the current user process.

## Fix

`dll.c` now has a single `Dll_FreeEntry` helper that releases the optional
mapped view, optional section handle, optional file handle, and `DLL_ENTRY`
allocation. `Dll_Load` calls the helper on any initialization failure before
returning `NULL`. `Dll_Unload` uses the same helper after removing successful
entries from `Dll_List`. `Dll_Load` now opens the DLL file with
`OBJ_CASE_INSENSITIVE | OBJ_KERNEL_HANDLE`.

Export parsing, syscall discovery, DLL names, PE layout logic, and list lookup
behavior are unchanged.

## Acceptance Gate

`docs/plan/check-srev-214.py` validates the draft-07 schema, official
references, source-level `Dll_FreeEntry` ownership shape, failure cleanup from
`Dll_Load`, unload cleanup from `Dll_Unload`, driver-private
`OBJ_KERNEL_HANDLE` attributes, split ledger fragment, and removal of the stale
partial-failure leak and successful-entry pool leak shapes.

Runtime/build gate: Windows driver build plus a loader failure-injection smoke
that exercises failure after file open, after section creation, and after view
mapping, proving no handle/view/pool leak under Driver Verifier or equivalent
pool/handle tracking. A normal driver init/unload smoke must prove successful
DLL entries still support syscall/export discovery and are freed at unload.
