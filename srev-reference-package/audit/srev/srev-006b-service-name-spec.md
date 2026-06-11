# SREV-006B Service Broker Name Shape

Status: source-level spec before patch.

## Official Shape

`OpenServiceW` accepts `lpServiceName` as `LPCWSTR`. Microsoft documents the
service name as the service object's name, not display name, with a maximum
string length of 256 characters. Service Control Manager compares names
case-insensitively and rejects invalid names.

Sources:

- https://learn.microsoft.com/en-us/windows/win32/api/winsvc/nf-winsvc-openservicew

## Local Shape

Sandboxie service broker requests carry a length-prefixed service name:

- `SERVICE_START_REQ.name_len`, `name[1]`
- `SERVICE_QUERY_REQ.name_len`, `name[1]`

The DLL-side caller sends `name_len = wcslen(name)` and includes the terminating
WCHAR in `h.length`. The service side must prove that same shape before passing
`req->name` to `OpenServiceW`.

## Local Risk

The previous service handlers checked that `name_len * sizeof(WCHAR)` bytes fit
inside the request, but did not require the terminating WCHAR to be present or
verify `name[name_len] == L'\0'` before calling `OpenServiceW`.

## Patch Boundary

Do not change service authorization or SCM access masks. Add a local service
name gate before `OpenServiceW`:

- `name_len <= 256`
- the name payload plus terminator fits inside `h.length`
- `name[name_len] == L'\0'`

## Acceptance Gate

- Start-service and query-service handlers both call the service-name gate.
- The service-name gate proves `(name_len + 1) * sizeof(WCHAR)` is inside the
  received message before `OpenServiceW`.
- `OpenServiceW` is not called for unterminated or overlong names.
- Runtime gate remains open: malformed broker messages return
  `ERROR_INVALID_PARAMETER`; normal service start/query requests still work.
