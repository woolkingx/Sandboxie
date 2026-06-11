---
kind: srev-ledger-entry
id: SREV-206
title: PStoreCreateInstance Output Contract
status: patched-source-level-after-official-pstore-output-loader-shape-review-needs-windows-runtime-proof
owner: Sandboxie/core/dll/pst.cpp
spec: docs/plan/srev-206-pstore-create-instance-output-contract.md
schema: docs/plan/srev-206-pstore-create-instance-output-contract.schema.json
checker: docs/plan/check-srev-206.py
runtime_gate: Windows DLL build plus Protected Storage smoke proving ordinary PStoreCreateInstance(&provider, NULL, NULL, 0) still returns a usable IPStore implementation and malformed caller arguments do not crash the hook path
---

### SREV-206: PStoreCreateInstance Output Contract

| Field | Content |
|---|---|
| Severity | [moderate] |
| Status | patched source-level after official PStore output/loader shape review; needs Windows runtime proof |
| Evidence | `Sandboxie/core/dll/pst.cpp` was the top unnamed reviewable core file after SREV-205. It hooks `pstorec.dll!PStoreCreateInstance` and returns a local `IPStoreImpl` when Protected Storage is not opened to the host. Before this fix, `Pst_PStoreCreateInstance` wrote through `ppProvider` without checking whether the caller supplied a valid output pointer, and it passed the result of `GetModuleHandle(DllName_ole32_or_combase)` directly to `GetProcAddress` without proving the module handle was non-NULL. |
| Data | `pst.cpp`, `Pst_PStoreCreateInstance`, `PStoreCreateInstance`, `IPStore`, `IPStoreImpl`, `ppProvider`, `pProviderID`, `pReserved`, `dwFlags`, `__sys_CoTaskMemAlloc`, `DllName_ole32_or_combase`, `GetModuleHandle`, `GetProcAddress`, `CoTaskMemAlloc`, `Pst_Init`, `SbieDll_InitPStore`, and `OpenProtectedStorage`. |
| Schema | `PSTORE_CREATE_INSTANCE_OUTPUT_CONTRACT` says `pst.cpp` owns the local Protected Storage hook boundary; `ppProvider` is an out pointer and must be validated before any write; on local failure after the output pointer is accepted, the output slot is cleared before returning failure; `GetProcAddress` may only be called after the `GetModuleHandle` result is proven non-NULL; success publishes a local `IPStoreImpl` and returns `S_OK`; and `pReserved` / `dwFlags` semantic fidelity remains a Windows runtime compatibility gate. |
| Topology | Legal flow is `sandboxed process -> pstorec.dll!PStoreCreateInstance -> Sandboxie hook Pst_PStoreCreateInstance -> ppProvider output gate -> ole32/combase module lookup -> CoTaskMemAlloc export lookup -> local IPStoreImpl publication -> caller-owned COM interface lifetime`. |
| Logic Risk | The old hook could crash the caller on a NULL `ppProvider`, and a missing `ole32`/`combase` module could send a NULL module handle into the dynamic export lookup path. Both are deterministic boundary failures that can be closed without changing Sandboxie's Protected Storage policy. The broader semantic question of unsupported `pReserved` or `dwFlags` values stays as runtime compatibility work because Microsoft documents the legal input shape but not the precise failure HRESULT for unsupported values. |
| Official Shape | `docs/plan/srev-206-pstore-create-instance-output-contract.md` records Microsoft `PStoreCreateInstance`, `IPStore`, `CoTaskMemAlloc`, `GetModuleHandleW`, and `GetProcAddress` references. `docs/plan/srev-206-pstore-create-instance-output-contract.schema.json` records the JSON Schema draft-07 local `PSTORE_CREATE_INSTANCE_OUTPUT_CONTRACT` contract. |
| Fix | `Pst_PStoreCreateInstance` now rejects NULL `ppProvider` with `E_POINTER`, clears the accepted output slot before any later failure, checks the module handle before resolving `CoTaskMemAlloc`, preserves the existing failure return when the allocator export is unavailable, and preserves the existing successful `IPStoreImpl` publication. |
| Acceptance Gate | `docs/plan/check-srev-206.py` validates the draft-07 schema, official references, source-level output-pointer and module-handle gates, successful `IPStoreImpl` publication, stale unchecked loader lookup removal, and split ledger fragment; `docs/plan/check-srev-206.sh` is the targeted wrapper. Runtime/build gate: Windows DLL build plus Protected Storage smoke proving ordinary `PStoreCreateInstance(&provider, NULL, NULL, 0)` still returns a usable `IPStore` implementation and malformed caller arguments do not crash the hook path. |
