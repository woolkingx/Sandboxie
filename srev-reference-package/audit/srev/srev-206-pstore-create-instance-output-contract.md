# SREV-206: PStoreCreateInstance Output Contract

## Stage

schema -> boundary -> topology -> logic -> action -> verify

## Evidence

`Sandboxie/core/dll/pst.cpp` was the top unnamed reviewable core file after
SREV-205. It hooks `pstorec.dll!PStoreCreateInstance` and returns a local
`IPStoreImpl` instead of letting protected-storage calls cross into the host
Protected Storage provider when `OpenProtectedStorage` is not configured.

Before this fix, `Pst_PStoreCreateInstance` wrote through `ppProvider` without
checking whether the caller supplied a valid output pointer. It also passed the
result of `GetModuleHandle(DllName_ole32_or_combase)` directly to
`GetProcAddress` without proving that the module handle was non-NULL.

## Data

`pst.cpp`, `Pst_PStoreCreateInstance`, `PStoreCreateInstance`, `IPStore`,
`IPStoreImpl`, `ppProvider`, `pProviderID`, `pReserved`, `dwFlags`,
`__sys_CoTaskMemAlloc`, `DllName_ole32_or_combase`, `GetModuleHandle`,
`GetProcAddress`, `CoTaskMemAlloc`, `Pst_Init`, `SbieDll_InitPStore`, and
`OpenProtectedStorage`.

## Official Shape

Microsoft documents `PStoreCreateInstance` as returning an `IPStore` provider
through `_Out_ IPStore **ppProvider`; the `ppProvider` parameter cannot be
NULL, `pProviderID` may be NULL to select the base storage provider, `pReserved`
must be NULL, and `dwFlags` must be zero. A successful return is `S_OK`.

Microsoft documents `IPStore` as the COM interface returned by
`PStoreCreateInstance` for Protected Storage operations.

Microsoft documents `CoTaskMemAlloc` as returning NULL when allocation fails,
and documents its export as living in `Ole32.dll`. This local hook stores the
function pointer so `IPStoreImpl` can allocate COM task memory consistently with
the COM ABI.

Microsoft documents `GetModuleHandleW` as returning NULL on failure, and
`GetProcAddress` as taking a module handle returned by loader APIs and returning
NULL on failure.

References:

- `https://learn.microsoft.com/en-us/windows/win32/devnotes/pstorecreateinstance`
- `https://learn.microsoft.com/en-us/windows/win32/devnotes/ipstore`
- `https://learn.microsoft.com/en-us/windows/win32/api/combaseapi/nf-combaseapi-cotaskmemalloc`
- `https://learn.microsoft.com/en-us/windows/win32/api/libloaderapi/nf-libloaderapi-getmodulehandlew`
- `https://learn.microsoft.com/en-us/windows/win32/api/libloaderapi/nf-libloaderapi-getprocaddress`

## Schema

`PSTORE_CREATE_INSTANCE_OUTPUT_CONTRACT` says:

- `pst.cpp` owns the local Protected Storage hook boundary for
  `PStoreCreateInstance`.
- `ppProvider` is an out pointer and must be validated before any write.
- On a local failure after the output pointer is accepted, the output slot is
  cleared before returning failure.
- `GetProcAddress` may only be called after the `GetModuleHandle` result is
  proven non-NULL.
- Success publishes a local `IPStoreImpl` and returns `S_OK`.
- `pReserved` and `dwFlags` semantic fidelity remains a Windows runtime
  compatibility gate because Microsoft documents the legal input shape but not
  the precise failure HRESULT for unsupported values.

## Topology

```text
sandboxed process
-> pstorec.dll!PStoreCreateInstance
-> Sandboxie hook Pst_PStoreCreateInstance
-> ppProvider output gate
-> ole32/combase module lookup
-> CoTaskMemAlloc export lookup
-> local IPStoreImpl publication
-> caller-owned COM interface lifetime
```

## Logic Risk

The old hook could crash the caller on a NULL `ppProvider`, and a missing
`ole32`/`combase` module could send a NULL module handle into the dynamic export
lookup path. Both are deterministic boundary failures that can be closed without
changing Sandboxie's Protected Storage policy.

The broader semantic question of whether non-NULL `pReserved` or non-zero
`dwFlags` should preserve original PStore HRESULT behavior is recorded as a
runtime compatibility gate, not patched from guesswork.

## Fix

`Pst_PStoreCreateInstance` now rejects NULL `ppProvider` with `E_POINTER`, clears
the accepted output slot before any later failure, checks the module handle
before resolving `CoTaskMemAlloc`, preserves the existing failure return when the
allocator export is unavailable, and preserves the existing successful
`IPStoreImpl` publication.

## Acceptance Gate

`docs/plan/check-srev-206.py` validates the draft-07 schema, official
references, source-level output-pointer and module-handle gates, successful
`IPStoreImpl` publication, stale unchecked loader lookup removal, and the split
ledger fragment. Runtime/build gate: Windows DLL build plus Protected Storage
smoke proving ordinary `PStoreCreateInstance(&provider, NULL, NULL, 0)` still
returns a usable `IPStore` implementation and malformed caller arguments do not
crash the hook path.
