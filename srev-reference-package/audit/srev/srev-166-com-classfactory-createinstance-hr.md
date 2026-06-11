# SREV-166: COM ClassFactory CreateInstance HRESULT

## Stage Gate

```text
stage: schema -> boundary -> topology -> logic -> action -> verify
input artifact: Sandboxie/core/svc/comserver9.c and Microsoft COM IClassFactory / IUnknown documentation
output artifact: simulated COM class factory returns the real object-creation HRESULT
owner: Sandboxie/core/svc/comserver9.c
acceptance gate: docs/plan/check-srev-166.py and docs/plan/check-srev-166.sh
```

## Data

`comserver9.c` simulates selected COM local-server objects so Sandboxie can
capture URL/navigation requests and restart the requested host program inside
the sandbox. Its class factory method:

```c
ComServer_IClassFactory_CreateInstance(
    IClassFactory *This, IUnknown *pUnkOuter, REFIID riid, void **ppvObject)
```

creates a local simulated object, calls `IUnknown_QueryInterface(obj, riid,
ppvObject)`, assigns `E_NOINTERFACE` when no object can be created, but before
this SREV always returned `S_OK` at the end.

## Official Shape

- Microsoft documents `IClassFactory::CreateInstance` as returning `S_OK` only
  when the specified object was created, `CLASS_E_NOAGGREGATION` when
  `pUnkOuter` is non-NULL and aggregation is unsupported, and `E_NOINTERFACE`
  when the object does not support the requested `riid`:
  `https://learn.microsoft.com/en-us/windows/win32/api/unknwn/nf-unknwn-iclassfactory-createinstance`.
- Microsoft documents `IUnknown::QueryInterface` rules: unsupported interfaces
  return `E_NOINTERFACE`, and successful interface queries must return stable
  object identity through `IID_IUnknown`:
  `https://learn.microsoft.com/en-us/windows/win32/com/rules-for-implementing-queryinterface`.

## Schema

`COM_CLASSFACTORY_CREATEINSTANCE_HRESULT` says:

- `comserver9.c` owns the simulated COM class factory implementation.
- `CreateInstance` must return `E_POINTER` for a null output pointer.
- `CreateInstance` must return `CLASS_E_NOAGGREGATION` when `pUnkOuter` is
  non-NULL.
- If `pMyCreateInstance` cannot create a matching object, `CreateInstance` must
  return `E_NOINTERFACE`.
- If object creation succeeds but `IUnknown_QueryInterface` fails for `riid`,
  `CreateInstance` must return that failure HRESULT and leave `*ppvObject` null.
- `S_OK` is legal only when the requested interface pointer is returned.
- This patch does not change simulated IE/WMP interface coverage, reference
  counting policy, COM registration, message-loop lifetime, or sandbox process
  restart behavior.
- Linux source gates are not Windows COM activation runtime proof.

## Topology

Legal simulated COM activation flow:

```text
CoRegisterClassObject
  -> ComServer_IClassFactory_CreateInstance(riid, ppvObject)
  -> pMyCreateInstance(riid)
  -> IUnknown_QueryInterface(obj, riid, ppvObject)
  -> return the HRESULT that describes the pointer state
```

The class factory is the boundary adapter between COM activation and the local
simulated IE/WMP objects. It must not hide a failed interface negotiation behind
`S_OK`.

## Logic Risk

Returning `S_OK` with `*ppvObject == NULL` violates COM caller expectations and
can turn an ordinary unsupported-interface result into a null-pointer use or
incorrect activation path in the COM client. It also hides which simulated
interface is missing, making compatibility diagnosis noisier.

## Fix

`ComServer_IClassFactory_CreateInstance` now returns `hr`, preserving the
existing `E_POINTER` and `CLASS_E_NOAGGREGATION` early returns and propagating
`IUnknown_QueryInterface` / `E_NOINTERFACE` results at the normal exit.

## Verification

Source-level gates:

```bash
python3 docs/plan/check-srev-166.py
bash docs/plan/check-srev-166.sh
python3 docs/plan/check-core-coverage.py
```

Full closure matrix:

```bash
python3 docs/plan/check-srev-166.py &&
bash docs/plan/check-srev-166.sh &&
python3 docs/plan/check-core-coverage.py &&
for s in docs/plan/check-srev-0*.sh docs/plan/check-srev-1*.sh docs/plan/check-kpath-0*.sh; do bash "$s"; done &&
git diff --check
```

Runtime/build gate: Windows service/COM-server build; IE/WMP simulated COM
activation smoke; unsupported-interface `CreateInstance` smoke proving
`E_NOINTERFACE` with null output; aggregation smoke proving
`CLASS_E_NOAGGREGATION`; normal URL restart flow.
