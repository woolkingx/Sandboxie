# SREV-152: PStore Timestamp Map View Lifetime

## Stage Gate

| Field | Value |
|---|---|
| Stage | action |
| Input artifact | `Sandboxie/core/dll/ipstore_impl.cpp`, `Sandboxie/core/dll/ipstore_impl.h`, Microsoft `CreateFileMapping`, `MapViewOfFile`, and `UnmapViewOfFile` references |
| Output artifact | `docs/plan/srev-152-pstore-timestamp-map-view-lifetime.schema.json`, `docs/plan/check-srev-152.py`, `docs/plan/check-srev-152.sh`, ledger fragment |
| Owner | IPStoreImpl shared protected-storage timestamp mapping |
| Acceptance gate | source checker plus full SREV/KPATH/core coverage matrix; Windows PStore runtime proof remains required |

## Evidence

`Sandboxie/core/dll/ipstore_impl.cpp` became the top unnamed reviewable core file
after SREV-151. `IPStoreImpl` creates or opens a named file mapping for an
8-byte shared timestamp, maps a view with `MapViewOfFile`, and stores that view
in `global_timestamp`.

Before this SREV, constructor code wrote `*global_timestamp` whenever it had
created the section, even if `MapViewOfFile` failed and returned `NULL`.
Destructor code closed the mapping handle but never unmapped a successful view.

Official references:

- https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-createfilemappinga
- https://learn.microsoft.com/en-us/windows/win32/api/memoryapi/nf-memoryapi-mapviewoffile
- https://learn.microsoft.com/en-us/windows/win32/api/memoryapi/nf-memoryapi-unmapviewoffile

## Data

`section`, `global_timestamp`, `_SectionName`, `CreateFileMapping`,
`OpenFileMapping`, `MapViewOfFile`, `UnmapViewOfFile`, `IPStoreImpl::IPStoreImpl`,
and `IPStoreImpl::~IPStoreImpl`.

## Schema

`PSTORE_TIMESTAMP_MAP_VIEW_LIFETIME` says:

- `section` is a file mapping object handle, not a mapped address.
- `global_timestamp` is a mapped view address returned by `MapViewOfFile`.
- `MapViewOfFile` may fail and return `NULL`; the timestamp pointer is legal to
  dereference only after a non-null check.
- A successful mapped view must be unmapped with `UnmapViewOfFile` before or
  during owner destruction.
- Closing the file mapping handle does not replace unmapping the view.

## Topology

Legal timestamp flow:

```text
OpenFileMapping/CreateFileMapping handle
  -> MapViewOfFile returns global_timestamp or NULL
  -> constructor writes initial timestamp only if global_timestamp != NULL
  -> read/write paths require global_timestamp
  -> destructor UnmapViewOfFile(global_timestamp)
  -> destructor CloseHandle(section)
```

## Logic Risk

The mapping handle and the mapped address are different nodes. Treating a
successful handle as proof of a successful view creates a constructor-time NULL
write if the view cannot be mapped. Treating `CloseHandle(section)` as enough
cleanup leaves the process view mapped for the lifetime of the process or until
the OS tears it down, which is the wrong owner boundary for an object with an
explicit destructor.

## Fix

`IPStoreImpl::IPStoreImpl` now initializes the shared timestamp only when
`MapViewOfFile` returned a non-null `global_timestamp`. `IPStoreImpl::~IPStoreImpl`
now calls `UnmapViewOfFile(global_timestamp)` before closing the section handle.

## Acceptance Gate

`docs/plan/check-srev-152.py` validates the draft-07 schema, official
references, constructor non-null map-view gate, destructor unmap-before-close
order, unchanged shared timestamp read/write topology, and the ledger fragment.
`docs/plan/check-srev-152.sh` is the matrix wrapper.

Runtime/build gate: Windows DLL build; PStore creation/open smoke proving
timestamp mapping works when `MapViewOfFile` succeeds; fault injection or low
resource smoke proving `MapViewOfFile` failure does not dereference `NULL`; leak
observation proving `UnmapViewOfFile` runs before the mapping handle is closed.
