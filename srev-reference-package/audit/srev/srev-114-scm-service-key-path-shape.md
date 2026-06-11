# SREV-114 SCM Service Key Path Shape

## Data

Owner file:

```text
Sandboxie/core/dll/scm.c
```

Reviewed nodes:

```text
Scm_OpenServiceWImpl
Scm_AllocServiceKeyPath
Scm_OpenKeyForService
Scm_DiscardKeyCache
Scm_ServicesKeyPath
SCM_SERVICE_NAME_MAX_CHARS
NtOpenKey
NtCreateKey
InitializeObjectAttributes
RtlInitUnicodeString
Key_UpdateMergeByPath
```

## Schema

`SCM_SERVICE_KEY_PATH_SHAPE` defines these local contracts:

- `OpenServiceW` service names follow the SCM service-name shape: non-empty,
  maximum 256 characters, case-insensitive comparisons, and no display-name
  substitution.
- Sandboxie's local service-handle payload stores a `tzuk` marker followed by
  the owned service-name string.
- Lower-casing applies only to the service-name payload, not to the marker.
- Service registry paths are composed from `Scm_ServicesKeyPath`, a single
  slash separator, and the service name.
- Service registry path buffers are sized from the actual base path and service
  name length, not from fixed stack or fixed temp-buffer guesses.
- `Scm_OpenKeyForService` owns the temporary path buffer until `NtOpenKey` or
  `NtCreateKey` returns.
- `Scm_DiscardKeyCache` invalidates both the Services root and the service
  subkey path without changing the caller-visible last-error value.
- Existing access masks, boxed-service lookup, SbieSvc query topology, key-cache
  invalidation intent, and handle marker layout are unchanged.

## Topology

Open service path:

```text
Scm_OpenServiceWImpl
  -> validate HANDLE_SERVICE_MANAGER
  -> validate non-empty service name
  -> validate service name <= SCM_SERVICE_NAME_MAX_CHARS
  -> Scm_DiscardKeyCache
      -> Key_UpdateMergeByPath(Services root)
      -> Scm_AllocServiceKeyPath
      -> Key_UpdateMergeByPath(Services\ServiceName)
      -> restore last error
  -> Scm_IsBoxedService
      -> Scm_OpenKeyForService
          -> Scm_AllocServiceKeyPath
          -> RtlInitUnicodeString
          -> InitializeObjectAttributes
          -> NtOpenKey / NtCreateKey
          -> Dll_Free(path)
  -> allocate local SC_HANDLE payload
      -> write marker
      -> copy service name
      -> lowercase service-name payload only
```

## Logic Risk

The previous source built `\REGISTRY\MACHINE\SYSTEM\CurrentControlSet\Services`
plus the service name into a fixed 128-WCHAR stack buffer in
`Scm_OpenKeyForService`. `Scm_DiscardKeyCache` used a fixed 256-WCHAR temporary
buffer for the same shape. Microsoft documents SCM service names as up to 256
characters, so both buffers were shorter than the legal input shape once the
registry base path and slash were included.

The local service handle has a marker before the service-name payload. The old
source called `_wcslwr(name)` on the marker address. This happened to be unlikely
to modify the marker bytes, but the legal data shape is marker plus payload, so
string operations belong on the payload address.

## Official Shape

- https://learn.microsoft.com/nl-nl/windows/win32/api/winsvc/nf-winsvc-openservicew
- https://learn.microsoft.com/en-us/windows/win32/api/winsvc/nf-winsvc-createservicea
- https://learn.microsoft.com/en-us/windows/win32/api/winsvc/nf-winsvc-closeservicehandle
- https://learn.microsoft.com/en-us/windows/win32/api/ntdef/nf-ntdef-initializeobjectattributes
- https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-zwopenkey
- https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-zwcreatekey
- https://learn.microsoft.com/en-us/windows/win32/sysinfo/registry-element-size-limits

## Fix

`Scm_OpenServiceWImpl` now rejects service names longer than
`SCM_SERVICE_NAME_MAX_CHARS` before any registry path construction and checks the
local handle-payload allocation. The service-name lower-case operation now starts
at the payload string after the `tzuk` marker.

`Scm_AllocServiceKeyPath` centralizes the `Services\ServiceName` path shape with
length-derived allocation. `Scm_OpenKeyForService` and `Scm_DiscardKeyCache` use
that helper instead of fixed local buffers. `Scm_DiscardKeyCache` preserves the
incoming last-error value because cache invalidation is not the public result of
the caller's SCM operation.

Access masks, boxed-service classification, SbieSvc query routing,
`NtOpenKey`/`NtCreateKey` use, error mapping, key-cache invalidation targets, and
local SC_HANDLE marker layout are unchanged.

## Acceptance Gate

Source gate:

```bash
python3 docs/plan/check-srev-114.py
bash docs/plan/check-srev-114.sh
```

Runtime gate still required:

- Windows matrix for `OpenServiceW` / `OpenServiceA` with short, 128-char,
  255-char, 256-char, and 257-char service names.
- Boxed service registry-key open with near-limit service names.
- `Scm_DiscardKeyCache` observation proving Services root and service subkey
  invalidation still happen.
- Invalid service-name matrix for empty, over-limit, slash, and backslash names.
- Existing BITS/WUAU/MSIServer/TrustedInstaller/CryptSvc compatibility paths.
