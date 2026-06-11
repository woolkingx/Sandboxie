---
kind: srev-ledger-entry
id: SREV-226
title: PStore Enumerator QueryInterface Contract
status: patched-source-level-after-official-com-queryinterface-and-local-pstore-enumerator-abi-review-needs-windows-pstore-runtime-proof
owner: Sandboxie/core/dll/ipstore_enum.cpp
spec: docs/plan/srev-226-pstore-enumerator-query-interface-contract.md
schema: docs/plan/srev-226-pstore-enumerator-query-interface-contract.schema.json
checker: docs/plan/check-srev-226.py
runtime_gate: "Windows DLL build plus PStore enumeration and QueryInterface ABI smokes"
---
### SREV-226: PStore Enumerator QueryInterface Contract

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official COM `QueryInterface` and local PStore enumerator ABI review; needs Windows PStore runtime proof |
| Evidence | `Sandboxie/core/dll/ipstore_enum.cpp` was the top unnamed reviewable core file after SREV-225. It implements `IEnumPStoreTypesImpl::QueryInterface` and `IEnumPStoreItemsImpl::QueryInterface` for local PStore COM enumerators. Before this SREV, both methods ignored the requested IID, unconditionally called `AddRef`, wrote `*ppvObject = this`, and returned `S_OK`. The generated ABI in `Sandboxie/core/dll/pstore.h` declares distinct `IID_IEnumPStoreTypes` and `IID_IEnumPStoreItems`; `Sandboxie/core/dll/ipstore_enum.h` shows the implementation classes inherit a non-COM state base before the COM interface base. |
| Data | `ipstore_enum.cpp`, `ipstore_enum.h`, `pstore.h`, `IEnumPStoreTypesImpl::QueryInterface`, `IEnumPStoreItemsImpl::QueryInterface`, `IID_IUnknown`, `IID_IEnumPStoreTypes`, `IID_IEnumPStoreItems`, `IEnumPStoreTypes`, and `IEnumPStoreItems`. |
| Schema | `PSTORE_ENUMERATOR_QUERY_INTERFACE_CONTRACT` says `pstore.h` owns the generated COM ABI; `ipstore_enum.cpp` owns the local enumerator implementations and the local `IID_IEnumPStoreTypes` / `IID_IEnumPStoreItems` definitions when no generated `pstore_i.c` IID object is linked; `QueryInterface` rejects null `ppvObject` with `E_POINTER`; succeeds only for `IID_IUnknown` and the concrete enumerator IID; unsupported IIDs set `*ppvObject = NULL` and return `E_NOINTERFACE`; successful queries publish the adjusted COM interface pointer and then `AddRef` it. |
| Topology | `IPStoreImpl::EnumTypes`, `EnumSubtypes`, and `EnumItems` return local PStore enumerators. Callers may then ask `QueryInterface(iid, ppvObject)`. The legal edge is from requested IID to the matching generated COM interface subobject, not to the unadjusted C++ implementation object. |
| Logic Risk | Returning `S_OK` for every IID lies about object capabilities and can hand callers an invalid interface. Writing through a null `ppvObject` can crash. Returning the unadjusted implementation pointer is also not the COM interface pointer contract for these multiple-inheritance classes. |
| Official Shape | `docs/plan/srev-226-pstore-enumerator-query-interface-contract.md` records Microsoft `IUnknown::QueryInterface` and QueryInterface implementation rules: null output returns `E_POINTER`, unsupported interfaces return `E_NOINTERFACE` and null output, supported interfaces return a pointer to the requested interface and call `AddRef`. |
| Fix | `IEnumPStoreTypesImpl::QueryInterface` now accepts only `IID_IUnknown` and `IID_IEnumPStoreTypes`, publishes `(IEnumPStoreTypes *)this`, then calls `AddRef`. `IEnumPStoreItemsImpl::QueryInterface` now accepts only `IID_IUnknown` and `IID_IEnumPStoreItems`, publishes `(IEnumPStoreItems *)this`, then calls `AddRef`. Both methods return `E_POINTER` for null `ppvObject` and set `*ppvObject = NULL` with `E_NOINTERFACE` for unsupported IIDs. `ipstore_enum.cpp` now defines the two local PStore enumerator IIDs using the UUIDs from `pstore.idl` / `pstore.h`, so the DLL links without a separate generated IID object. No PStore enumeration contents, ordering, merge policy, service broker requests, `Next`, `Skip`, `Reset`, `Clone`, or reference-count deletion behavior changed. |
| Acceptance Gate | `docs/plan/check-srev-226.py` validates the draft-07 schema, official references, generated PStore IID/interface declarations, local IID definitions, multiple-inheritance topology, corrected QueryInterface gates and adjusted pointer publication for both enumerator classes, stale `*ppvObject = this` removal, and ledger entry; `docs/plan/check-srev-226.sh` is the targeted wrapper. Runtime/build gate: Windows DLL build; PStore enumeration smoke; legal IID QueryInterface smokes; and unsupported IID/null-output smokes. |
