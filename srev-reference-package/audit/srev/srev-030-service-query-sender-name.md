# SREV-030: Service Query Sender Name Shape

## Finding

`Sandboxie/core/dll/scm_query.c` builds `SERVICE_QUERY_REQ` in a fixed stack
union:

```c
union {
    SERVICE_QUERY_REQ req;
    WCHAR req_space[384];
} u;
```

The old code assigned `name_len = wcslen(ServiceNm)` and then used
`wcscpy(u.req.name, ServiceNm)` before SbieSvc could validate the request. This
left the sender side with a fixed-buffer overflow risk for overlong real service
names.

SREV-006B already validated the receiver side before `OpenServiceW`; this
finding closes the matching sender boundary.

## Official API Shape

Primary Microsoft reference:

- `https://learn.microsoft.com/en-us/windows/win32/api/winsvc/nf-winsvc-openservicew`

Relevant contract:

- `OpenServiceW` takes a null-terminated `LPCWSTR` service name.
- Microsoft documents the maximum service name length as 256 characters.
- The service name is the service object name, not the display name.

## Local Schema

Small machine-readable schema:

```text
docs/plan/srev-030-service-query.schema.json
```

Request:

```text
MSG_HEADER
with_service_status
with_service_config
name_len
name[(name_len + 1) WCHAR]
```

`name_len` is a WCHAR count and excludes the terminating NUL.

## Source Change

`Scm_QueryServiceByName` now:

- rejects NULL service names before any service lookup;
- lets boxed-service names stay on the boxed-service path;
- rejects real service names longer than `SCM_SERVICE_NAME_MAX_CHARS`;
- computes `req_len` before writing the stack union;
- verifies `req_len <= sizeof(u)`;
- copies `(name_len + 1) * sizeof(WCHAR)` bytes with `memcpy` instead of
  unbounded `wcscpy`.

## Acceptance Gate

Source-level gate:

- `docs/plan/check-srev-030.py` validates the `SERVICE_QUERY` schema and source
  guard/copy shape.
- No `wcscpy(u.req.name, ServiceNm)` remains.

Windows runtime gate:

- Query a normal real service at legal maximum length and at maximum + 1.
- Query a boxed service path to confirm boxed services still bypass the real SCM
  sender constraint.
- Confirm malformed/overlong real service names fail before `SbieDll_CallServer`.
