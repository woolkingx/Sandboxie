---
kind: srev-ledger-entry
id: SREV-166
title: COM ClassFactory CreateInstance HRESULT
status: patched-source-needs-windows-runtime
owner: Sandboxie/core/svc/comserver9.c
spec: docs/plan/srev-166-com-classfactory-createinstance-hr.md
schema: docs/plan/srev-166-com-classfactory-createinstance-hr.schema.json
checker: docs/plan/check-srev-166.py
runtime_gate: "Windows COM-server build, simulated IE/WMP COM activation smoke, unsupported-interface CreateInstance smoke, aggregation smoke, and normal URL restart flow"
---

### SREV-166: COM ClassFactory CreateInstance HRESULT

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after Microsoft COM `IClassFactory::CreateInstance` and `IUnknown::QueryInterface` review; needs Windows COM activation runtime proof |
| Evidence | `Sandboxie/core/svc/comserver9.c` was the top unnamed reviewable core file after SREV-165. Its `ComServer_IClassFactory_CreateInstance` simulates COM local-server activation for IE/WMP navigation capture. Before this SREV, it assigned `hr` from `IUnknown_QueryInterface` or `E_NOINTERFACE`, but returned `S_OK` unconditionally at the normal exit. |
| Data | `Sandboxie/core/svc/comserver9.c`, `ComServer_IClassFactory_CreateInstance`, `IClassFactory::CreateInstance`, `IUnknown_QueryInterface`, `pMyCreateInstance`, `ppvObject`, `riid`, `S_OK`, `E_POINTER`, `CLASS_E_NOAGGREGATION`, `E_NOINTERFACE`, and `HRESULT`. |
| Schema | `COM_CLASSFACTORY_CREATEINSTANCE_HRESULT` says `comserver9.c` owns the simulated COM class factory implementation; `CreateInstance` must return `E_POINTER` for a null output pointer; `CLASS_E_NOAGGREGATION` when `pUnkOuter` is non-NULL; `E_NOINTERFACE` when no matching object/interface exists; and `S_OK` only when the requested interface pointer is returned. |
| Topology | Legal flow is `CoRegisterClassObject` -> `ComServer_IClassFactory_CreateInstance(riid, ppvObject)` -> `pMyCreateInstance(riid)` -> `IUnknown_QueryInterface(obj, riid, ppvObject)` -> return the HRESULT that describes the pointer state. |
| Logic Risk | Returning `S_OK` with `*ppvObject == NULL` violates COM caller expectations and can turn an ordinary unsupported-interface result into a null-pointer use or incorrect activation path in the COM client. It also hides which simulated interface is missing, making compatibility diagnosis noisier. |
| Official Shape | `docs/plan/srev-166-com-classfactory-createinstance-hr.md` records Microsoft `IClassFactory::CreateInstance` and `IUnknown::QueryInterface` references. `docs/plan/srev-166-com-classfactory-createinstance-hr.schema.json` records the JSON Schema draft-07 local `COM_CLASSFACTORY_CREATEINSTANCE_HRESULT` contract. |
| Fix | `ComServer_IClassFactory_CreateInstance` now returns `hr`, preserving the existing `E_POINTER` and `CLASS_E_NOAGGREGATION` early returns and propagating `IUnknown_QueryInterface` / `E_NOINTERFACE` results at the normal exit. Simulated IE/WMP interface coverage, reference counting policy, COM registration, message-loop lifetime, and sandbox process restart behavior are unchanged. |
| Acceptance Gate | `docs/plan/check-srev-166.py` validates the draft-07 schema, official references, `CreateInstance` early returns, `IUnknown_QueryInterface` propagation, rejection of the stale unconditional `S_OK`, and ledger entry; `docs/plan/check-srev-166.sh` is the matrix wrapper. Runtime/build gate: Windows service/COM-server build; IE/WMP simulated COM activation smoke; unsupported-interface `CreateInstance` smoke proving `E_NOINTERFACE` with null output; aggregation smoke proving `CLASS_E_NOAGGREGATION`; normal URL restart flow. |
