# SREV-123 SCM Create Request Allocation Lifetime

## Data

Owner file:

```text
Sandboxie/core/dll/scm_create.c
```

Reviewed nodes:

```text
Scm_AddBoxedService
Scm_CreateServiceW
Scm_StartBoxedService2
Dll_AllocTemp
Dll_Alloc
Dll_Free
Scm_GetBoxedServices
SandboxedServices
SERVICE_RUN_REQ
SbieDll_CallServer
ERROR_NOT_ENOUGH_MEMORY
STATUS_INSUFFICIENT_RESOURCES
```

## Schema

`SCM_CREATE_REQUEST_ALLOCATION_LIFETIME` defines these local contracts:

- `Dll_Alloc` and `Dll_AllocTemp` may fail before returning a writable buffer.
- `Scm_AddBoxedService` writes the updated `SandboxedServices` `REG_MULTI_SZ`
  only after the temporary `names2` buffer exists.
- `Scm_CreateServiceW` allocates the returned service-handle name buffer before
  writing the handle marker or service name into it.
- `Scm_CreateServiceW` allocates the service-handle name buffer before adding
  the service to the SbieSvc `SandboxedServices` list, so allocation failure
  does not leave a service-list entry without a returned handle.
- If `Scm_AddBoxedService` fails after the handle-name buffer was allocated,
  `Scm_CreateServiceW` frees that buffer before deleting the partially created
  service key.
- `Scm_StartBoxedService2` writes and sends `SERVICE_RUN_REQ` only after the
  request buffer exists.
- `Scm_StartBoxedService2` frees the request buffer after `SbieDll_CallServer`
  returns.
- Service type, start type, error control, display name, image path, object
  name, sandboxed-service list semantics, special service routing, and service
  run wire shape are unchanged.

## Topology

```text
Scm_AddBoxedService
  -> Scm_GetBoxedServices()
  -> Dll_AllocTemp(names2)
  -> append service name to REG_MULTI_SZ
  -> NtSetValueKey(SandboxedServices)
  -> Dll_Free(names2)

Scm_CreateServiceW
  -> create service registry key
  -> write Type / Start / ErrorControl / optional strings
  -> Dll_Alloc(handle-name buffer)
  -> fill local fake SC_HANDLE payload
  -> Scm_AddBoxedService(service name)
  -> return fake SC_HANDLE or free buffer and delete key

Scm_StartBoxedService2
  -> derive service image path
  -> Dll_Alloc(SERVICE_RUN_REQ + path)
  -> fill MSGID_SERVICE_RUN request
  -> SbieDll_CallServer
  -> Dll_Free(request)
  -> return service-run Win32 error
```

## Logic Risk

The old code treated local allocation as infallible. `Scm_AddBoxedService`
could write into a null `names2` pointer. `Scm_CreateServiceW` could write the
fake service-handle marker and service name into a null `name` pointer after it
had already created the service key and added the service to the boxed-service
list. `Scm_StartBoxedService2` could write a `SERVICE_RUN_REQ` into a null
request buffer and also leaked the request buffer on the normal call-server
path.

The correct local repair is an allocation and ownership gate at each data node.
It does not change SCM policy, requested service access, special boxed service
routing, service configuration values, service-start permissions, or the
service-run wire contract.

## Official Shape

- https://learn.microsoft.com/en-us/windows/win32/api/heapapi/nf-heapapi-heapalloc
- https://learn.microsoft.com/en-us/windows/win32/api/heapapi/nf-heapapi-heapfree
- https://learn.microsoft.com/en-us/windows/win32/api/winsvc/nf-winsvc-createservicew
- https://learn.microsoft.com/en-us/windows/win32/api/winsvc/nf-winsvc-startservicew

## Fix

`Scm_AddBoxedService` now checks `names2` after `Dll_AllocTemp` and returns
`STATUS_INSUFFICIENT_RESOURCES` through the existing mutex/list cleanup path
before writing the updated `REG_MULTI_SZ`.

`Scm_CreateServiceW` now checks the fake service-handle name allocation before
writing into it. The allocation is performed before `Scm_AddBoxedService`; if
the list update later fails, the allocated handle-name buffer is freed before
the partially created service key is deleted. Allocation failure now returns
`ERROR_NOT_ENOUGH_MEMORY` instead of dereferencing a null pointer.

`Scm_StartBoxedService2` now checks the `SERVICE_RUN_REQ` allocation before
filling the request. It frees any special-service heap path on allocation
failure and frees the request buffer immediately after `SbieDll_CallServer`
returns.

No service creation policy, registry value shape, sandboxed-service list key,
special service name routing, device map capture, request `msgid`, service run
path copy, or call-server reply handling changed.

## Acceptance Gate

Source gate:

```bash
python3 docs/plan/check-srev-123.py
bash docs/plan/check-srev-123.sh
```

Runtime/build gate still required:

- Windows build for `scm_create.c`.
- Allocation-failure injection for `Scm_AddBoxedService` proving no write to a
  null `names2` buffer and mutex/list cleanup still runs.
- Allocation-failure injection for `Scm_CreateServiceW` fake-handle allocation
  proving the partially created service key is deleted and no
  `SandboxedServices` entry is added.
- Failure injection for `Scm_AddBoxedService` after fake-handle allocation
  proving the fake-handle buffer is freed before key deletion.
- Allocation-failure injection for `Scm_StartBoxedService2` proving special
  heap path cleanup and `ERROR_NOT_ENOUGH_MEMORY`.
- Positive boxed service create/start smoke proving unchanged registry values,
  boxed-service list update, service-run request, and reply handling.
