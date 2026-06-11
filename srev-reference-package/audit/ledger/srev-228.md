---
kind: srev-ledger-entry
id: SREV-228
title: Taskbar Property Store QueryInterface Contract
status: patched-source-level-after-official-ipropertystore-queryinterface-review-needs-windows-taskbar-runtime-proof
owner: Sandboxie/core/dll/propsys.h
spec: docs/plan/srev-228-taskbar-property-store-query-interface.md
schema: docs/plan/srev-228-taskbar-property-store-query-interface.schema.json
checker: docs/plan/check-srev-228.py
runtime_gate: "Windows DLL build plus taskbar property store wrapper and QueryInterface ABI smokes"
---
### SREV-228: Taskbar Property Store QueryInterface Contract

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official `IPropertyStore` / `QueryInterface` review; needs Windows taskbar runtime proof |
| Evidence | `Sandboxie/core/dll/propsys.h` was the top unnamed reviewable core file after SREV-227. It is the local Vista/7 SDK shim for the `IPropertyStore` ABI. The execution owner is `Sandboxie/core/dll/taskbar.c`, whose `Taskbar_SHGetPropertyStoreForWindow` wraps shell `IPropertyStore` objects. Before this SREV, `Taskbar_Unknown_QueryInterface` accepted only `IID_IPropertyStore`, did not return `E_POINTER` for null `ppv`, and did not clear `*ppv` on unsupported IIDs. Microsoft documents `IPropertyStore` as inheriting from `IUnknown`, and documents `QueryInterface` as the IID-based identity/interface query that returns `E_POINTER` for null output and `E_NOINTERFACE` with null output for unsupported interfaces. |
| Data | `propsys.h`, `taskbar.c`, `IPropertyStore`, `IID_IPropertyStore`, `Taskbar_IID_IUnknown`, `SHGetPropertyStoreForWindow`, `Taskbar_SHGetPropertyStoreForWindow`, `Taskbar_Unknown_QueryInterface`, `Taskbar_Unknown_AddRef`, and `Taskbar_Unknown_Release`. |
| Schema | `TASKBAR_PROPERTY_STORE_QUERY_INTERFACE_CONTRACT` says `propsys.h` owns the local `IPropertyStore` ABI shim; `taskbar.c` owns the Sandboxie wrapper returned from `SHGetPropertyStoreForWindow`; `IPropertyStore` inherits from `IUnknown`, so the wrapper must support both `IID_IUnknown` and `IID_IPropertyStore`; null output is `E_POINTER`; unsupported IIDs set null output and return `E_NOINTERFACE`; successful queries publish the supported interface pointer and then `AddRef` it. |
| Topology | Caller asks shell for a window property store, Sandboxie wraps only successful `IID_IPropertyStore` requests, and later COM callers may query the wrapper for identity or the property-store interface. The wrapper forwards property methods and rewrites AppUserModelID-related values, but the COM identity surface is still `IUnknown`. |
| Logic Risk | Rejecting `IID_IUnknown` makes the wrapper an invalid COM identity surface. Writing through a null output pointer can crash. Leaving `*ppv` untouched on `E_NOINTERFACE` can leave callers with stale interface pointers. |
| Official Shape | `docs/plan/srev-228-taskbar-property-store-query-interface.md` records Microsoft `IPropertyStore`, `SHGetPropertyStoreForWindow`, `IUnknown::QueryInterface`, and QueryInterface implementation-rule references. |
| Fix | `taskbar.c` now defines local `Taskbar_IID_IUnknown`. `Taskbar_Unknown_QueryInterface` returns `E_POINTER` when `ppv` is null, accepts `Taskbar_IID_IUnknown` and `IID_IPropertyStore`, writes `*ppv = This`, then calls `AddRef`. Unsupported IIDs set `*ppv = NULL` and return `E_NOINTERFACE`. No AppUserModelID rewriting, property forwarding, real property-store lifetime forwarding, hook install conditions, or `SHGetPropertyStoreForWindow` pass-through behavior changed. |
| Acceptance Gate | `docs/plan/check-srev-228.py` validates the draft-07 schema, official references, `propsys.h` ABI evidence, taskbar GUID constants, corrected `Taskbar_Unknown_QueryInterface` gates, property-store wrapper topology preservation, and ledger entry; `docs/plan/check-srev-228.sh` is the targeted wrapper. Runtime/build gate: Windows DLL build; taskbar property-store smoke; `QueryInterface(IID_IUnknown)` / `IID_IPropertyStore` success smokes; and unsupported IID/null-output smokes. |
