# SREV-228 Taskbar Property Store QueryInterface Contract

## Data

Owner files:

```text
Sandboxie/core/dll/propsys.h
Sandboxie/core/dll/taskbar.c
```

Reviewed nodes:

```text
IPropertyStore
IID_IPropertyStore
IID_IUnknown
SHGetPropertyStoreForWindow
Taskbar_SHGetPropertyStoreForWindow
Taskbar_Unknown_QueryInterface
Taskbar_Unknown_AddRef
Taskbar_Unknown_Release
```

## Schema

`TASKBAR_PROPERTY_STORE_QUERY_INTERFACE_CONTRACT` defines these local contracts:

- `propsys.h` is the local Vista/7 SDK shim for the `IPropertyStore` ABI.
- `taskbar.c` owns the Sandboxie wrapper returned from
  `SHGetPropertyStoreForWindow`.
- `IPropertyStore` inherits from `IUnknown`, so the wrapper must support
  `IID_IUnknown` and `IID_IPropertyStore`.
- `QueryInterface` must reject a null output pointer with `E_POINTER` before
  writing through it.
- Unsupported IIDs must set `*ppv = NULL` and return `E_NOINTERFACE`.
- Successful queries must publish the supported interface pointer and then
  `AddRef` it.
- This SREV does not change AppUserModelID rewriting, relaunch property
  rewriting, property forwarding, real property-store lifetime forwarding, hook
  install conditions, or `SHGetPropertyStoreForWindow` pass-through behavior for
  unsupported requested interfaces.

## Topology

```text
caller
  -> SHGetPropertyStoreForWindow(hwnd, IID_IPropertyStore, &ppv)
  -> real shell IPropertyStore
  -> Sandboxie Taskbar property-store wrapper
  -> wrapper QueryInterface(IID_IUnknown or IID_IPropertyStore)
  -> wrapper forwarding and AppUserModelID rewriting
```

The wrapper is a COM object. The legal identity edge is `IUnknown`, while the
legal behavior edge is `IPropertyStore`. A wrapper that supports only the
behavior IID is not a valid COM identity surface.

## Logic Risk

Before this SREV, `Taskbar_Unknown_QueryInterface` rejected every IID except
`IID_IPropertyStore`, did not check `ppv` before writing through it, and did not
clear the output pointer on `E_NOINTERFACE`. That violates the COM
`QueryInterface` contract for an `IPropertyStore` wrapper because
`IPropertyStore` inherits from `IUnknown`.

The minimal legal fix is to add the local `IID_IUnknown` constant, accept both
legal IIDs, publish the wrapper interface pointer, call `AddRef` only on
success, and set null output on unsupported IIDs.

## Official Shape

- https://learn.microsoft.com/en-us/windows/win32/api/propsys/nn-propsys-ipropertystore
- https://learn.microsoft.com/en-us/windows/win32/api/shellapi/nf-shellapi-shgetpropertystoreforwindow
- https://learn.microsoft.com/en-us/windows/win32/api/unknwn/nf-unknwn-iunknown-queryinterface%28refiid_void%29
- https://learn.microsoft.com/en-us/windows/win32/com/rules-for-implementing-queryinterface

## Fix

`taskbar.c` now has a local `Taskbar_IID_IUnknown` constant for the COM identity
IID. `Taskbar_Unknown_QueryInterface` returns `E_POINTER` for null `ppv`,
accepts `Taskbar_IID_IUnknown` and `IID_IPropertyStore`, writes `*ppv = This`
before `AddRef`, and sets `*ppv = NULL` before returning `E_NOINTERFACE` for
unsupported IIDs.

No taskbar AppUserModelID rewriting, property forwarding, or shell property
store acquisition behavior changed.

## Acceptance Gate

Source gate:

```bash
bash docs/plan/check-srev-228.sh
python3 docs/plan/check-core-coverage.py
git diff --check
```

Full historical matrix is deferred to the next batch checkpoint or shared
checker/ledger infrastructure change.

Runtime/build gate still required:

- Windows DLL build for `propsys.h` and `taskbar.c`.
- Taskbar property-store smoke proving `SHGetPropertyStoreForWindow` still wraps
  `IID_IPropertyStore` requests and forwards property methods.
- COM ABI smoke proving wrapper `QueryInterface(IID_IUnknown)` and
  `QueryInterface(IID_IPropertyStore)` succeed, and unsupported IIDs return
  `E_NOINTERFACE` with null output.
