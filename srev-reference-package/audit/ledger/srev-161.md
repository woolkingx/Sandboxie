---
kind: srev-ledger-entry
id: SREV-161
title: PStore Enumerator End Contract
status: patched-source-needs-windows-runtime
owner: Sandboxie/core/svc/pstoreserver.cpp
spec: docs/plan/srev-161-pstore-enumerator-end-contract.md
schema: docs/plan/srev-161-pstore-enumerator-end-contract.schema.json
checker: docs/plan/check-srev-161.py
runtime_gate: "Windows SbieSvc build, host pstorec.dll enumeration smoke, empty enumeration smoke, and sandboxed credential/PStore merge smoke"
---

### SREV-161: PStore Enumerator End Contract

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after Protected Storage COM ABI and COM enumerator `Next` shape review; needs Windows PStore runtime proof |
| Evidence | `Sandboxie/core/dll/pstore.h` was the top unnamed reviewable core file after SREV-160. It is a MIDL-generated Protected Storage COM ABI header declaring `IPStore::EnumTypes`, `IPStore::EnumSubtypes`, `IPStore::EnumItems`, `IEnumPStoreTypes::Next`, and `IEnumPStoreItems::Next`. `Sandboxie/core/svc/pstoreserver.cpp` consumes those host COM enumerators and converts them into `PStoreWire.h` replies. Before this SREV, `PStoreServer::EnumTypes` and `PStoreServer::EnumItems` used `while (SUCCEEDED(hr))` as the item loop after `Next(1, ..., &n)`, even though COM end-of-sequence can be `S_FALSE`, which still satisfies `SUCCEEDED`. The second `EnumItems` pass could then copy from an unset `name` pointer, and `EnumTypes` built a long reply but returned `S_OK` instead of the reply packet pointer. |
| Data | `Sandboxie/core/dll/pstore.h`, `Sandboxie/core/svc/pstorewire.h`, `Sandboxie/core/svc/pstoreserver.cpp`, `IPStore::EnumTypes`, `IPStore::EnumSubtypes`, `IPStore::EnumItems`, `IEnumPStoreTypes::Next`, `IEnumPStoreItems::Next`, `PSTORE_ENUM_TYPES_RPL`, `PSTORE_ENUM_ITEMS_RPL`, `S_OK`, `S_FALSE`, fetched counts, item names, GUID arrays, `CoTaskMemFree`, and `LONG_REPLY`. |
| Schema | `PSTORE_ENUMERATOR_END_CONTRACT` says `pstore.h` is the ABI/schema evidence for the PStore COM interfaces; `pstoreserver.cpp` owns the service-side PStore enumeration broker; successful `IPStore::EnumTypes`, `IPStore::EnumSubtypes`, and `IPStore::EnumItems` calls must produce non-null enumerator interface pointers; `Next(1, ..., &fetched)` yields exactly one item only when `hr == S_OK` and `fetched == 1`; `S_FALSE`, local `ERROR_NO_MORE_ITEMS`, or any successful result with `fetched == 0` is end-of-enumeration, not another item; end-of-enumeration is normalized to `S_OK` in the Sandboxie reply after all fetched items have been copied; unexpected successful `Next` shapes fail as `E_UNEXPECTED`; `EnumTypes` returns the `LONG_REPLY` packet pointer; and this SREV does not change PStore read/write policy, current-user versus local-machine lookup order, wire struct layout, prompt suppression, or local sandboxed PStore merge behavior. |
| Topology | Legal flow is sandboxed DLL request, SbieSvc `PStoreServer`, host `IPStore` enumeration, one-item `Next` calls gated by `S_OK + fetched 1`, recognized end-of-enumeration normalized to reply success, and `PSTORE_ENUM_TYPES_RPL` / `PSTORE_ENUM_ITEMS_RPL` returned to the caller. |
| Logic Risk | `SUCCEEDED(S_FALSE)` is true, so treating success as item availability can hang the SbieSvc PStore worker at normal enumeration end or copy from an uninitialized item-name pointer. Returning an HRESULT from a `MSG_HEADER *` handler also discards the allocated broker reply. |
| Official Shape | `docs/plan/srev-161-pstore-enumerator-end-contract.md` records Microsoft `IPStore`, `IPStore::EnumItems`, `IPStore::EnumSubtypes`, `IEnumVARIANT::Next`, and `IEnumBitsPeers::Next` references. `docs/plan/srev-161-pstore-enumerator-end-contract.schema.json` records the JSON Schema draft-07 local `PSTORE_ENUMERATOR_END_CONTRACT` contract. |
| Fix | `pstoreserver.cpp` now uses `PStore_IsEnumEnd` to recognize `S_FALSE`, local `ERROR_NO_MORE_ITEMS`, and successful zero-fetch results as end-of-enumeration. `EnumTypes` and `EnumItems` count or copy elements only for `hr == S_OK` plus one fetched element. Unexpected successful non-item/non-end results become `E_UNEXPECTED`. `EnumItems` initializes and frees returned names on all paths. `EnumTypes` uses `return (MSG_HEADER *)rpl;`. |
| Acceptance Gate | `docs/plan/check-srev-161.py` validates the draft-07 schema, official references, generated `pstore.h` ABI surface, `PStoreWire` reply records, `PStore_IsEnumEnd`, non-null enumerator gates, one-item `Next` gating, end normalization, stale `SUCCEEDED(hr)` copy path removal, `EnumTypes` reply-pointer return, and ledger entry; `docs/plan/check-srev-161.sh` is the matrix wrapper. Runtime/build gate: Windows SbieSvc build, host `pstorec.dll` enumeration smoke where `Next` returns `S_OK` for items and `S_FALSE` at the end, empty type/subtype/item enumerations, and sandboxed credential/PStore merge smoke proving no enumeration hang and a valid reply packet. |
