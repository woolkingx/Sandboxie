# SREV-161: PStore Enumerator End Contract

## Stage Gate

```text
stage: schema -> boundary -> topology -> logic -> action -> verify
input artifact: Sandboxie/core/dll/pstore.h, Sandboxie/core/svc/pstorewire.h, and Sandboxie/core/svc/pstoreserver.cpp
output artifact: COM enumerator end-of-sequence handling for PStore broker replies
owner: Sandboxie/core/svc/pstoreserver.cpp
acceptance gate: docs/plan/check-srev-161.py and docs/plan/check-srev-161.sh
```

## Data

`pstore.h` is a MIDL-generated Protected Storage COM ABI header. It declares
`IPStore::EnumTypes`, `IPStore::EnumSubtypes`, and `IPStore::EnumItems` as
returning `IEnumPStoreTypes` / `IEnumPStoreItems` enumerator interfaces.
`pstoreserver.cpp` is the service-side broker that calls the host `pstorec.dll`
COM object, converts enumerated GUIDs or item names into Sandboxie's
`PStoreWire.h` replies, and sends those replies to the sandboxed DLL.

Before this SREV, `PStoreServer::EnumTypes` and `PStoreServer::EnumItems`
iterated with `while (SUCCEEDED(hr))` after each `Next(1, ..., &n)` call. COM
enumerators use a fetched-count plus HRESULT shape: reaching the end can return
`S_FALSE`, and `S_FALSE` still satisfies `SUCCEEDED`. That made the broker
liable to loop forever on a normal end-of-sequence result. In the second
`EnumItems` pass, the same logic could treat an end result as an item and copy
from an unset `name` pointer. `EnumTypes` also built a long reply but returned
`S_OK` instead of returning the allocated reply packet.

## Official Shape

- Microsoft documents `IPStore` as a Protected Storage COM interface. It is a
  legacy interface that may be unavailable on newer Windows versions and
  inherits from `IUnknown`:
  `https://learn.microsoft.com/en-us/windows/win32/devnotes/ipstore`.
- Microsoft documents `IPStore::EnumItems` as returning an
  `IEnumPStoreItems` interface pointer used to enumerate protected-storage
  items:
  `https://learn.microsoft.com/en-us/windows/win32/devnotes/ipstore-enumitems`.
- Microsoft documents `IPStore::EnumSubtypes` as returning an
  `IEnumPStoreTypes` interface for subtype enumeration:
  `https://learn.microsoft.com/en-us/windows/win32/devnotes/ipstore-enumsubtypes`.
- Microsoft documents the COM enumerator `Next` shape through
  `IEnumVARIANT::Next`: `S_OK` means the requested count was returned,
  `S_FALSE` means fewer items were returned, and the fetched count records the
  actual number:
  `https://learn.microsoft.com/en-us/windows/win32/api/oaidl/nf-oaidl-ienumvariant-next`.
- Microsoft documents the same `S_OK` / `S_FALSE` fetched-count contract for
  another COM enumerator, `IEnumBitsPeers::Next`:
  `https://learn.microsoft.com/en-us/windows/win32/api/bits3_0/nf-bits3_0-ienumbitspeers-next`.

## Schema

`PSTORE_ENUMERATOR_END_CONTRACT` says:

- `pstore.h` is the ABI/schema evidence for the PStore COM interfaces.
- `pstoreserver.cpp` owns the service-side PStore enumeration broker.
- `IPStore::EnumTypes`, `IPStore::EnumSubtypes`, and `IPStore::EnumItems`
  produce COM enumerator interfaces; those interface pointers must be non-null
  after a successful factory call.
- `Next(1, ..., &fetched)` yields exactly one item only when `hr == S_OK` and
  `fetched == 1`.
- `S_FALSE`, local `ERROR_NO_MORE_ITEMS`, or any successful result with
  `fetched == 0` is end-of-enumeration, not another item.
- end-of-enumeration is normalized to `S_OK` in the Sandboxie reply after all
  fetched items have been copied.
- an unexpected successful `Next` result with neither one fetched item nor a
  recognized end shape fails as `E_UNEXPECTED`.
- `EnumTypes` returns the `LONG_REPLY` packet pointer, not an HRESULT value.
- this SREV does not change PStore read/write policy, current-user versus
  local-machine lookup order, wire struct layout, prompt suppression, or local
  sandboxed PStore merge behavior.

## Topology

Legal type/subtype enumeration flow:

```text
sandboxed DLL -> PSTORE_ENUM_TYPES_REQ
SbieSvc PStoreServer -> host IPStore::EnumTypes or EnumSubtypes
IEnumPStoreTypes::Next -> {S_OK + fetched 1 => append GUID}
                      -> {S_FALSE or fetched 0 => enumeration end}
PStoreServer -> PSTORE_ENUM_TYPES_RPL with count and GUID array
```

Legal item enumeration flow:

```text
sandboxed DLL -> PSTORE_ENUM_ITEMS_REQ
SbieSvc PStoreServer -> host IPStore::EnumItems
first pass -> count names and reply bytes only for S_OK + fetched 1 + name
second pass -> copy only S_OK + fetched 1 + name
end result -> reply status S_OK
error result -> reply status is the failing HRESULT
```

## Logic Risk

`SUCCEEDED(S_FALSE)` is true. A broker loop that treats `SUCCEEDED(hr)` as
"there is another element" confuses COM transport success with enumeration
state. On a standard COM end-of-sequence result, the service can spin forever,
or in the `EnumItems` reply-copy pass read an unset `name` pointer. Returning
`S_OK` from a function whose contract is `MSG_HEADER *` also discards the long
reply that the broker just allocated.

## Fix

`pstoreserver.cpp` now has a local `PStore_IsEnumEnd` helper that recognizes
`S_FALSE`, local `ERROR_NO_MORE_ITEMS`, and successful zero-fetch results as
enumeration end. `EnumTypes` and `EnumItems` require `hr == S_OK` plus a fetched
count of one before counting or copying an element. Unexpected successful
non-item/non-end shapes become `E_UNEXPECTED`. `EnumItems` initializes and frees
the returned name pointer on every path. `EnumTypes` now returns the allocated
reply packet pointer.

## Verification

Source-level gates:

```bash
python3 docs/plan/check-srev-161.py
bash docs/plan/check-srev-161.sh
python3 docs/plan/check-core-coverage.py
```

Full closure matrix:

```bash
python3 docs/plan/check-srev-161.py &&
bash docs/plan/check-srev-161.sh &&
python3 docs/plan/check-core-coverage.py &&
for s in docs/plan/check-srev-0*.sh docs/plan/check-srev-1*.sh docs/plan/check-kpath-0*.sh; do bash "$s"; done &&
git diff --check
```

Runtime/build gate: Windows SbieSvc build; host `pstorec.dll` enumeration smoke
where `Next` returns `S_OK` for items and `S_FALSE` at the end; empty type,
subtype, and item enumerations; sandboxed credential/PStore merge smoke proving
the broker returns a reply packet and does not hang at enumeration end.
