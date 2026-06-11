# SREV-226 PStore Enumerator QueryInterface Contract

## Data

Owner files:

```text
Sandboxie/core/dll/ipstore_enum.cpp
Sandboxie/core/dll/ipstore_enum.h
Sandboxie/core/dll/pstore.h
```

Reviewed nodes:

```text
IEnumPStoreTypesImpl::QueryInterface
IEnumPStoreItemsImpl::QueryInterface
IID_IUnknown
IID_IEnumPStoreTypes
IID_IEnumPStoreItems
IEnumPStoreTypes
IEnumPStoreItems
```

## Schema

`PSTORE_ENUMERATOR_QUERY_INTERFACE_CONTRACT` defines these local contracts:

- `pstore.h` owns the generated COM ABI and declares
  `IID_IEnumPStoreTypes`, `IID_IEnumPStoreItems`, `IEnumPStoreTypes`, and
  `IEnumPStoreItems`.
- `ipstore_enum.cpp` owns the local COM enumerator implementations returned by
  `IPStoreImpl::EnumTypes`, `EnumSubtypes`, and `EnumItems`.
- Because this repository carries the MIDL header without a compiled
  `pstore_i.c` IID object, `ipstore_enum.cpp` also owns the local definitions
  for `IID_IEnumPStoreTypes` and `IID_IEnumPStoreItems` that its
  `QueryInterface` gates compare against.
- `QueryInterface` must reject a null `ppvObject` with `E_POINTER` before
  writing through it.
- `QueryInterface` must return `S_OK` only for `IID_IUnknown` and the concrete
  enumerator IID implemented by that object.
- Unsupported IIDs must set `*ppvObject = NULL` and return `E_NOINTERFACE`.
- Successful queries must publish the adjusted COM interface pointer, not the
  unadjusted C++ implementation object pointer.
- Successful queries must `AddRef` the returned interface.
- This SREV does not change PStore enumeration contents, ordering, merge
  policy, service broker requests, `Next`, `Skip`, `Reset`, `Clone`, or
  reference-count deletion behavior.

## Topology

```text
IPStoreImpl::EnumTypes / EnumSubtypes / EnumItems
  -> IEnumPStoreTypesImpl or IEnumPStoreItemsImpl
  -> caller QueryInterface(iid, ppvObject)
  -> {IID_IUnknown or own enum IID => adjusted interface pointer + AddRef}
  -> {unsupported IID => NULL + E_NOINTERFACE}
```

`IEnumPStoreGeneric` is a local implementation base with state. It is not a COM
interface. The legal COM boundary is the generated `IEnumPStoreTypes` or
`IEnumPStoreItems` interface from `pstore.h`, so `QueryInterface` must return
that interface subobject pointer.

The local IID values are the UUIDs from `pstore.idl` / `pstore.h`:

```text
IEnumPStoreItems = 4C83B307-0B70-4726-8F75-396EBBDAA401
IEnumPStoreTypes = 4C83B307-0B70-4726-8F75-396EBBDAA402
```

## Logic Risk

Before this SREV, both PStore enumerator `QueryInterface` implementations
ignored the requested IID, unconditionally called `AddRef`, wrote `this` through
`ppvObject`, and returned `S_OK`. A null output pointer could crash the caller.
An unsupported IID could receive a success result and a pointer to an unrelated
interface. Because these classes use multiple inheritance with a non-COM state
base before the COM interface base, returning the unadjusted implementation
object pointer is not the same contract as returning the requested COM interface
pointer.

The minimal legal fix is to gate the output pointer, restrict accepted IIDs to
`IUnknown` and the concrete enum interface, publish the adjusted interface
pointer, and fail unsupported IIDs with a null output.

## Official Shape

- https://learn.microsoft.com/en-us/windows/win32/api/unknwn/nf-unknwn-iunknown-queryinterface%28refiid_void%29
- https://learn.microsoft.com/en-us/windows/win32/com/rules-for-implementing-queryinterface

Microsoft documents `QueryInterface` as an IID-based query that returns
`E_POINTER` for a null output pointer, returns `E_NOINTERFACE` and null output
for unsupported interfaces, and calls `AddRef` on a supported returned interface
pointer.

## Fix

`IEnumPStoreTypesImpl::QueryInterface` now accepts only `IID_IUnknown` and
`IID_IEnumPStoreTypes`, returns `(IEnumPStoreTypes *)this`, and calls `AddRef`
only after publishing a supported interface pointer.

`IEnumPStoreItemsImpl::QueryInterface` now accepts only `IID_IUnknown` and
`IID_IEnumPStoreItems`, returns `(IEnumPStoreItems *)this`, and calls `AddRef`
only after publishing a supported interface pointer.

Both implementations return `E_POINTER` for null `ppvObject`; unsupported IIDs
set `*ppvObject = NULL` and return `E_NOINTERFACE`.

`ipstore_enum.cpp` now also defines the two local PStore enumerator IIDs so the
DLL links when no generated `pstore_i.c` IID object is part of the project.

No enumeration data flow, broker wire shape, local/host PStore merge behavior,
or `Next`/`Skip`/`Reset`/`Clone` behavior changed.

## Acceptance Gate

Source gate:

```bash
bash docs/plan/check-srev-226.sh
python3 docs/plan/check-core-coverage.py
git diff --check
```

Full historical matrix is deferred to the next batch checkpoint or shared
checker/ledger infrastructure change.

Runtime/build gate still required:

- Windows DLL build for `ipstore_enum.cpp`, `ipstore_enum.h`, and `pstore.h`.
- PStore enumeration smoke proving `EnumTypes`, `EnumSubtypes`, and `EnumItems`
  still return usable enumerators.
- COM ABI smoke proving `QueryInterface(IID_IUnknown)`,
  `QueryInterface(IID_IEnumPStoreTypes)`, and
  `QueryInterface(IID_IEnumPStoreItems)` succeed on their legal owners and
  unsupported IIDs return `E_NOINTERFACE` with a null output pointer.
